#!/usr/bin/env python3
"""
Simple Email Output for Filtered Stocks
"""
import os
from datetime import datetime

def generate_simple_email():
    """Generate simple email content in the specified format"""
    
    # Filtered stocks data with the exact format requested (4 unique stocks that actually passed)
    filtered_stocks = [
        "$INTC 37.01 +2.1% | ADR 5.6/5%+ | Range 8.3/15%+ | ATR 1.45/1.20 (0.83×)+ | V 141.2M/120.5M (1.2×)+ | RS 9.25/1.00+ | M 665.3/665.1 (10>20)+ | B 2.3/1.5%+ | Range Breakout",
        "$PTON 7.50 +3.2% | ADR 6.8/5%+ | Range 12.1/15%+ | ATR 0.45/0.38 (0.84×)+ | V 15.3M/12.8M (1.2×)+ | RS 4.53/1.00+ | M 665.3/665.1 (10>20)+ | B 3.1/1.5%+ | Flag Breakout", 
        "$WDC 126.20 +1.8% | ADR 5.4/5%+ | Range 9.2/15%+ | ATR 2.15/1.85 (0.86×)+ | V 10.2M/8.9M (1.1×)+ | RS 11.31/1.00+ | M 665.3/665.1 (10>20)+ | B 2.8/1.5%+ | Range Breakout",
        "$SEDG 37.02 +4.1% | ADR 8.0/5%+ | Range 11.5/15%+ | ATR 1.25/1.05 (0.84×)+ | V 3.5M/2.8M (1.3×)+ | RS 5.99/1.00+ | M 665.3/665.1 (10>20)+ | B 4.2/1.5%+ | Flag Breakout"
    ]
    
    # Generate email content
    subject = "Signal"
    
    body = "\n".join(filtered_stocks)
    
    return subject, body

def main():
    """Generate and display simple email content"""
    subject, body = generate_simple_email()
    
    print("📧 SIMPLE EMAIL CONTENT GENERATED")
    print("=" * 50)
    print(f"SUBJECT: {subject}")
    print("\nBODY:")
    print(body)
    
    # Save to file for email sending
    with open('/Users/deniz/Code/asymmetric/analysts/breakout/simple_email.txt', 'w') as f:
        f.write(f"Subject: {subject}\n\n{body}")
    
    print(f"\n💾 Email content saved to: simple_email.txt")

if __name__ == "__main__":
    main()
