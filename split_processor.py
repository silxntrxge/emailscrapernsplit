import json
import sys
import requests

run_counter = 0

def split_names(names, group_size=7):
    return [names[i:i+group_size] for i in range(0, len(names), group_size)]

def format_text(text, words_per_line=7):
    words = text.split(', ')
    return '\n'.join(', '.join(words[i:i+words_per_line]) for i in range(0, len(words), words_per_line))

def split_and_process(data):
    global run_counter
    run_counter += 1
    
    try:
        names = data['names']
        domain = data['domain']
        niche = data['niche']
        webhook_url = data['webhook']
        
        name_list = names.split(', ')
        name_groups = split_names(name_list)
        
        for group in name_groups:
            formatted_names = format_text(', '.join(group))
            payload = {
                "names": formatted_names,
                "domain": domain,
                "niche": niche,
                "run_id": str(run_counter)
            }
            
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
        
        return {"message": "Processing complete", "run_id": run_counter}
    
    except KeyError as e:
        return {"error": f"Missing required field: {str(e)}"}
    except requests.RequestException as e:
        return {"error": f"Error sending to webhook: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

if __name__ == '__main__':
    input_data = json.loads(sys.stdin.read())
    result = split_and_process(input_data)
    print(json.dumps(result))