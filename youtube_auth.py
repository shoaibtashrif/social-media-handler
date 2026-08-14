import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these scopes, delete the file youtube_token.json.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def main():
    creds = None
    token_path = 'youtube_token.json'
    client_secrets_file = 'client_secrets.json'
    
    if not os.path.exists(client_secrets_file):
        print(f"Error: {client_secrets_file} not found in this directory.")
        return

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Failed to refresh: {e}. Re-authenticating...")
                creds = None

        if not creds:
            print("Starting authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES)
            # We use a static port if possible, or 0 for random.
            # However, in remote environments, run_console is better, but Google deprecated run_console.
            # Using run_local_server(port=8080) and we can port-forward or use the URL.
            # Let's try port=8080, if not 8081, etc.
            try:
                creds = flow.run_local_server(port=8080, open_browser=False)
            except OSError:
                creds = flow.run_local_server(port=0, open_browser=False)
            
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            print(f"\nAuthentication successful! Token saved to {token_path}")
    else:
        print(f"\nAlready authenticated! Credentials valid in {token_path}")

if __name__ == '__main__':
    main()
