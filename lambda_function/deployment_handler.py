# deployment_handler.py
import os
import shutil
import subprocess

def prepare_deployment():
    # Create deployment directory
    if os.path.exists('lambda_function'):
        shutil.rmtree('lambda_function')
    os.makedirs('lambda_function')

    # Copy Python files
    python_files = ['main.py', 'leader_agent.py', 'api_keys.py']
    for file in python_files:
        shutil.copy(file, 'lambda_function/')

    # Copy requirements.txt
    shutil.copy('requirements.txt', 'lambda_function/')

    # Install dependencies in the lambda_function directory
    subprocess.run([
        'pip',
        'install',
        '-r',
        'requirements.txt',
        '--target',
        'lambda_function/'
    ])

    print("Deployment package prepared successfully!")

if __name__ == "__main__":
    prepare_deployment()