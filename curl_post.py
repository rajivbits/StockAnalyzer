import requests
import json

def invoke_lambda_function(url, instruction):
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Prepare the payload
    payload = {
        "body": json.dumps(instruction)  # Ensure the instruction is JSON formatted
    }
    
    # Make the POST request to the Lambda function URL
    response = requests.post(url, headers=headers, json=payload)
    
    # Check for success
    if response.status_code == 200:
        return response.json()  # Return the JSON response from Lambda
    else:
        print(f"Error invoking Lambda: {response.status_code} - {response.text}")
        return None

# Example usage
if __name__ == "__main__":
    lambda_url = "https://rpxj6nkp5nxzvsq7khg4vkegte0tulax.lambda-url.us-east-1.on.aws/"
    
    instruction = {
        "query": "Do the analysis of the stocks for the last 4 months Reliance, ONGC, Oil India, Indian Oil and HPC from NSE data and then let me know the rank wise stock performance based on their daily return"
    }
    
    result = invoke_lambda_function(lambda_url, instruction)
    
    if result:
        print("Lambda Response:", result)
