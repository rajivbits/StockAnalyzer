import json
from leader_agent import LeaderAgent

def lambda_handler(event, context):
    try:
        instruction = event['body']
        leader_agent = LeaderAgent()
        response = leader_agent.main(instruction)
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
