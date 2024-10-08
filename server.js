const express = require('express');
const { spawn } = require('child_process');
const fs = require('fs');
const axios = require('axios');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 10000;

// Add this logging middleware
app.use((req, res, next) => {
    console.log(`Received ${req.method} request for ${req.url}`);
    next();
});

// Existing /post endpoint (unchanged)
app.post('/', (req, res) => {
    console.log('Received POST request:', req.body);
    const { names, domain, niche, webhook } = req.body;

    // Write the configuration to a file
    const config = JSON.stringify({ names, domain, niche });
    fs.writeFileSync('config.json', config);

    console.log('Starting email scraping process...');
    const pythonProcess = spawn('python3', ['scraper.py']);

    let pythonOutput = '';

    pythonProcess.stdout.on('data', (data) => {
        console.log(`Python stdout: ${data}`);
        pythonOutput += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python Error: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python script exited with code ${code}`);
        
        if (code === 0) {
            // Read the emails from the file
            fs.readFile('emails.txt', 'utf8', (err, data) => {
                if (err) {
                    console.error('Error reading emails file:', err);
                    res.status(500).send('Error reading emails');
                    return;
                }

                const emails = data.split('\n').filter(email => email.trim() !== '');

                // Send the webhook
                axios.post(webhook, { emails })
                    .then(() => {
                        console.log('Webhook sent successfully');
                        res.status(200).send('Emails scraped and webhook sent');
                    })
                    .catch((error) => {
                        console.error('Error sending webhook:', error);
                        res.status(500).send('Error sending webhook');
                    });
            });
        } else {
            console.error('Error during scraping process:', pythonOutput);
            res.status(500).send('Error during scraping process');
        }
    });
});

// Modified /split endpoint
app.post('/split', (req, res) => {
    console.log('Received /split request:', req.body);

    const pythonProcess = spawn('python3', ['scraper.py', 'split']);

    pythonProcess.stdin.write(JSON.stringify(req.body));
    pythonProcess.stdin.end();

    let pythonOutput = '';

    pythonProcess.stdout.on('data', (data) => {
        console.log(`Python stdout: ${data}`);
        pythonOutput += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python Error: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python script exited with code ${code}`);
        
        if (code === 0) {
            try {
                const result = JSON.parse(pythonOutput);
                res.status(200).json(result);
            } catch (error) {
                console.error('Error parsing Python output:', error);
                res.status(500).send('Error processing split request');
            }
        } else {
            console.error('Error during split process:', pythonOutput);
            res.status(500).send('Error during split process');
        }
    });
});

// Add a catch-all route for debugging
app.use((req, res) => {
    console.log(`404 - Not Found: ${req.method} ${req.url}`);
    res.status(404).send('Not Found');
});

// Add this line just before app.listen()
console.log('Routes:', app._router.stack.filter(r => r.route).map(r => r.route.path));

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});