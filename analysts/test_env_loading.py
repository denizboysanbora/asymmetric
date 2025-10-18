#!/usr/bin/env python3
"""
Test script to verify environment variable loading and fallback behavior
"""
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_environment_loading():
    """Test the environment variable loading mechanism"""
    print("🧪 Testing Environment Variable Loading")
    print("=" * 50)
    
    # Check initial environment state
    initial_api_key = os.getenv("ALPACA_API_KEY")
    initial_secret_key = os.getenv("ALPACA_SECRET_KEY")
    
    print(f"Initial environment state:")
    print(f"  ALPACA_API_KEY: {'✓' if initial_api_key else '✗'}")
    print(f"  ALPACA_SECRET_KEY: {'✓' if initial_secret_key else '✗'}")
    
    # Test dotenv loading
    try:
        from dotenv import load_dotenv
        env_file_path = Path(__file__).parent / "config" / "api_keys.env"
        
        if env_file_path.exists():
            print(f"\n📁 Found .env file at: {env_file_path}")
            load_dotenv(env_file_path)
            
            # Check post-load state
            post_load_api_key = os.getenv("ALPACA_API_KEY")
            post_load_secret_key = os.getenv("ALPACA_SECRET_KEY")
            
            print(f"Post-load environment state:")
            print(f"  ALPACA_API_KEY: {'✓' if post_load_api_key else '✗'}")
            print(f"  ALPACA_SECRET_KEY: {'✓' if post_load_secret_key else '✗'}")
            
            if post_load_api_key and post_load_secret_key:
                print("✅ Environment loading successful!")
                return True
            else:
                print("❌ Environment loading failed!")
                return False
        else:
            print(f"⚠️  No .env file found at: {env_file_path}")
            return False
            
    except ImportError:
        print("❌ python-dotenv not available")
        return False

def test_network_connectivity():
    """Test network connectivity to Alpaca"""
    print("\n🌐 Testing Network Connectivity")
    print("=" * 50)
    
    try:
        import socket
        import urllib.request
        import urllib.error
        
        # Test DNS resolution
        try:
            socket.gethostbyname('data.alpaca.markets')
            print("✅ DNS resolution: data.alpaca.markets")
        except socket.gaierror as e:
            print(f"❌ DNS resolution failed: {e}")
            return False
        
        # Test HTTPS connectivity with API headers
        try:
            # Load API keys for the test
            from dotenv import load_dotenv
            from pathlib import Path
            env_file = Path(__file__).parent / "config" / "api_keys.env"
            if env_file.exists():
                load_dotenv(env_file)
            
            api_key = os.getenv("ALPACA_API_KEY")
            secret_key = os.getenv("ALPACA_SECRET_KEY")
            
            if api_key and secret_key:
                req = urllib.request.Request('https://data.alpaca.markets/v2/stocks/SPY/bars/latest')
                req.add_header('APCA-API-KEY-ID', api_key)
                req.add_header('APCA-API-SECRET-KEY', secret_key)
                urllib.request.urlopen(req, timeout=5)
                print("✅ HTTPS connectivity: data.alpaca.markets API")
                return True
            else:
                print("❌ API keys not available for connectivity test")
                return False
        except (urllib.error.URLError, socket.timeout) as e:
            print(f"❌ HTTPS connectivity failed: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Network diagnostics unavailable: {e}")
        return False

def test_liquid_stocks_function():
    """Test the get_liquid_stocks function"""
    print("\n📊 Testing get_liquid_stocks Function")
    print("=" * 50)
    
    try:
        from breakout_analysis import get_liquid_stocks
        
        print("Calling get_liquid_stocks()...")
        symbols = get_liquid_stocks()
        
        print(f"✅ Function returned {len(symbols)} symbols")
        print(f"First 10 symbols: {symbols[:10]}")
        
        return True
        
    except Exception as e:
        print(f"❌ get_liquid_stocks failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Environment Loading and Fallback Test Suite")
    print("=" * 60)
    
    # Test 1: Environment loading
    env_success = test_environment_loading()
    
    # Test 2: Network connectivity
    network_success = test_network_connectivity()
    
    # Test 3: Liquid stocks function
    function_success = test_liquid_stocks_function()
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 50)
    print(f"Environment Loading: {'✅ PASS' if env_success else '❌ FAIL'}")
    print(f"Network Connectivity: {'✅ PASS' if network_success else '❌ FAIL'}")
    print(f"Liquid Stocks Function: {'✅ PASS' if function_success else '❌ FAIL'}")
    
    if all([env_success, function_success]):
        print("\n🎉 All critical tests passed! The system should work correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
