from nsetools import Nse
nse = Nse()
from nsepython import *
from lambda_function.api_keys import *
import requests
import math
import pandas as pd
from datetime import datetime, timedelta
import time
import json
import re
from dateutil.relativedelta import relativedelta

## Initializing the Groq LLM Client
from groq import Groq
llm_client = Groq(api_key = groq_key)
        
class LeaderAgent:

    def __init__(self):

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        self.session = requests.Session()
        self.base_url = "https://www.nseindia.com"
        
        # Common stock symbol mappings
        
        self.company_list = nsefetch('https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O')
        df = pd.DataFrame(self.company_list['data'])
        
        self.common_symbols=dict()
        for idx, row in df.iterrows():
            self.common_symbols.update({row['meta']['symbol']: row['meta']['companyName']})

    def _get_cookies(self):

        """Get fresh cookies from NSE"""
        try:
            # Clear existing cookies
            self.session.cookies.clear()
            
            # Get initial cookies
            response = self.session.get(
                self.base_url,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"Failed to get cookies: {response.status_code}")
                return False

            # Add additional required headers
            self.headers['referer'] = self.base_url
            
            # Wait briefly
            time.sleep(1)
            return True
            
        except Exception as e:
            print(f"Error getting cookies: {e}")
            return False

    def get_quote_data(self, symbol):
        """Get current quote data for a symbol"""
        try:
            url = f"{self.base_url}/api/quote-equity?symbol={symbol}"
            print(url)
            response = self.session.get(url, headers=self.headers)
            print(response.status_code)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def get_historical_data(self, symbol, start_date, end_date):
        """Get historical data for a symbol with improved error handling"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Refresh cookies before each attempt
                if not self._get_cookies():
                    print("Failed to refresh cookies")
                    retry_count += 1
                    continue

                # Format dates
                from_date = start_date.strftime('%d-%m-%Y')
                to_date = end_date.strftime('%d-%m-%Y')
                
                # First get current quote data to ensure symbol is valid
                quote = self.get_quote_data(symbol)
                print(quote)
                if not quote:
                    print(f"Could not validate symbol: {symbol}")
                    return None

                # Construct URL for historical data
                url = f"{self.base_url}/api/historical/cm/equity?symbol={symbol}&series=[%22EQ%22]&from={from_date}&to={to_date}"
                
                response = self.session.get(
                    url,
                    headers=self.headers,
                    timeout=15
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        if 'data' in data and data['data']:
                            return pd.DataFrame(data['data'])
                        else:
                            print(f"No data available for {symbol}")
                            return None
                    except json.JSONDecodeError:
                        print(f"Invalid JSON response for {symbol}")
                        retry_count += 1
                        time.sleep(2)
                        continue
                else:
                    print(f"Error status code {response.status_code} for {symbol}")
                    retry_count += 1
                    time.sleep(2)
                    continue
                    
            except requests.exceptions.RequestException as e:
                print(f"Request error for {symbol}: {str(e)}")
                retry_count += 1
                time.sleep(2)
                continue
                
            except Exception as e:
                print(f"Unexpected error for {symbol}: {str(e)}")
                retry_count += 1
                time.sleep(2)
                continue
                
        print(f"Failed to get data for {symbol} after {max_retries} attempts")
        return None

    def match_company_to_symbol(self, company_name):
        """Match company name to NSE symbol"""
        company_name = company_name.lower().strip()
        
        # Direct abbreviation matches
        abbreviation_map = {
            # 'hpc': 'HINDPETRO',
            # 'ioc': 'IOC',
            # 'ongc': 'ONGC',
            # 'oil': 'OIL',
            # 'reliance': 'RELIANCE'
        }
        
        # Look for matches in common symbols
        for symbol, full_name in self.common_symbols.items():
            if company_name in full_name.lower():
                return symbol
                
        return None

    def calculate_stock_metrics(self,df):
        """Calculate various stock performance metrics"""
        df['Date'] = pd.to_datetime(df['CH_TIMESTAMP'])
        df['Close'] = pd.to_numeric(df['CH_CLOSING_PRICE'])
        df = df.sort_values('Date')
        
        # Weekly returns
        weekly_data = df.set_index('Date')['Close'].resample('W').last()
        weekly_returns = weekly_data.pct_change().dropna()
        
        metrics = {
            'avg_weekly_return': weekly_returns.mean() * 100,
            'total_return': ((df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100),
            'volatility': weekly_returns.std() * 100 * math.sqrt(52),
            'current_price': df['Close'].iloc[-1],
            'start_price': df['Close'].iloc[0],
            'highest_price': df['Close'].max(),
            'lowest_price': df['Close'].min()
        }
        
        return metrics

    def analyze_stocks(self,query):
        """Analyze stocks based on natural language query"""
        # Parse timeframe from query
        timeframe_match = re.search(r'last\s+(\d+)\s+months?', query)
        months = int(timeframe_match.group(1)) if timeframe_match else 3
        """
        Generate performance analysis using Llama
        """
        
        prompt = f"""
        f"I have the following document:\n\n"
    f"{query}\n\n"
    f"Please analyze this text and match it against the following company names:\n"
    f"{', '.join(list(self.common_symbols.values()))}.\n\n"
    f"Return high-confidence matches along with their descriptions if available. Also
    lookout of the abbreviated forms and focus more on fuzzy string match. Give the output in a 
    structured key value format like a JSON"
        """
        
        completion = llm_client.chat.completions.create(
            model="llama3-8b-8192",
            temperature = 0.6,
            seed = 123,
            response_format = { "type": "json_object" },
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt} \n"
                },
            ],
            stop="```",
        )
        
        
        print(completion.choices[0].message.content)

        # Parse the JSON string into a Python dictionary
        data = json.loads(completion.choices[0].message.content)

        # Extract descriptions from the matches
        self.companies = [match['description'] for match in data['matches']]
        print("Company names retrieved", self.companies)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - relativedelta(months=months)
        
        print(f"\nAnalysis Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Initialize client
        nse_client = NSEClient()
        
        # Match company names to symbols
        matched_symbols = {}
        unmatched_companies = []
        
        print("\nMatching company names to NSE symbols...")
        for company in self.companies:
            symbol = nse_client.match_company_to_symbol(company)
            if symbol:
                matched_symbols[company] = symbol
                print(f"Matched '{company}' to symbol: {symbol}")
            else:
                unmatched_companies.append(company)
                print(f"Could not match '{company}' to any NSE symbol")
        
        if unmatched_companies:
            print("\nWarning: The following companies could not be matched:")
            for company in unmatched_companies:
                print(f"- {company}")
        
        if not matched_symbols:
            print("No valid symbols found to analyze.")
            return None
        
        # Store results
        stock_results = {}
        
        print("\nFetching and analyzing stock data...")
        for company, symbol in matched_symbols.items():
            print(f"Processing {company} ({symbol})...")
            
            # Get historical data with retries
            # df = nse_client.get_historical_data(symbol, start_date, end_date)
            series = "EQ"
            df = equity_history(symbol, series, 
                                datetime.strptime(str(start_date).split()[0],'%Y-%m-%d').strftime('%d-%m-%Y'), 
                                datetime.strptime(str(end_date).split()[0],'%Y-%m-%d').strftime('%d-%m-%Y'))
            
            if df is not None and not df.empty:
                metrics = self.calculate_stock_metrics(df)
                stock_results[company] = {
                    'symbol': symbol,
                    **metrics
                }
                
            # Add delay between requests
            time.sleep(1)
        
        # Create rankings
        if stock_results:
            rankings = pd.DataFrame.from_dict(stock_results, orient='index')
            rankings = rankings.sort_values('avg_weekly_return', ascending=False)
            return rankings
        else:
            print("No data available for analysis")
            return None

    def format_results(self,rankings):
        """Format the analysis results for display"""
        print("\nStock Performance Rankings:")
        print("=" * 120)
        print(f"{'Company':<15} {'Symbol':<10} {'Avg Weekly':>12} {'Total':>10} {'Volatility':>10} {'Current':>12} {'Range':>25}")
        print(f"{'':15} {'':10} {'Return %':>12} {'Return %':>10} {'%':>10} {'Price INR':>12} {'(Low-High) INR':>25}")
        print("-" * 120)
        
        for index, row in rankings.iterrows():
            price_range = f"INR {row['lowest_price']:,.2f} - INR{row['highest_price']:,.2f}"
            print(f"{index:<15} {row['symbol']:<10} {row['avg_weekly_return']:>12.2f} {row['total_return']:>10.2f} "
                f"{row['volatility']:>10.2f} {row['current_price']:>12.2f} {price_range:>25}")

    def main(self,query):
        print("Analyzing query:", query)
        rankings = self.analyze_stocks(query)
        
        if rankings is not None:
            self.format_results(rankings)

            """
            Generate performance analysis using Llama
            """
            
            prompt = f"""
            Analyze the following weekly stock returns and provide a summary of performance:
            
            Average Weekly Returns (%):
            {rankings}
            
            Provide insights about:
            1. Ranking of stocks by performance
            2. Notable trends or patterns
            3. Best and worst performing stocks
            """
            
            completion = llm_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt} \n"
                    },
                ],
                stop="```",
            )

            
            print(completion.choices[0].message.content or "", end="")

if __name__ == "__main__":
    query = "Do the analysis of the stocks for the last 4 months Reliance, ONGC, Oil India, Indian Oil and HPC from NSE data and then let me know the rank wise stock performance based on their daily return"
    agent = LeaderAgent()
    agent.main(query)