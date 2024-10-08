import json
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

run_counter = 0

def split_names(names, group_size=7):
    return [names[i:i+group_size] for i in range(0, len(names), group_size)]

def format_text(text, words_per_line=7):
    words = text.split(', ')
    return '\n'.join(', '.join(words[i:i+words_per_line]) for i in range(0, len(words), words_per_line))

@app.route('/split', methods=['POST'])
def split_and_process():
    global run_counter
    run_counter += 1
    
    try:
        data = request.json
        names = data['names']
        webhook_url = data['webhook']
        
        name_list = names.split(', ')
        name_groups = split_names(name_list)
        
        for group in name_groups:
            formatted_names = format_text(', '.join(group))
            payload = {
                "names": formatted_names,
                "run_id": str(run_counter)
            }
            
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
        
        return jsonify({"message": "Processing complete", "run_id": run_counter}), 200
    
    except KeyError as e:
        return jsonify({"error": f"Missing required field: {str(e)}"}), 400
    except requests.RequestException as e:
        return jsonify({"error": f"Error sending to webhook: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)