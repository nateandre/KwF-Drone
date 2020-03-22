""" This program is intended to pull data for a list of given stocks and calculating their Betas & Alphas along with
    their measure of idiosyncratic risk based on the standard deviation of their residuals with respect to the CAPM.
    The Russell 2000 will be used as the market return rate, and the period of returns will be monthly based on user input
    (defaults to 60 automatically). The risk free rate used is the yields for 1month treasury bonds. Data for stock returns 
    was "provided for free by IEX". Note - ticker for Russell 2000 is IWM.

    Beta,alpha is calculated as the linear regression of (market ret. - risk free rate) and (stock ret. - risk free rate).
    idiosyncratic risk is calculated as sqrt(total variance of stock ret. - (beta^2 * total var. of market returns))

    MAKE sure that stocks.txt is in the same directory. This program returns a csv titled stock_summary.csv with alpha,
    beta,and idiosyncratic risk measures for each stock.

    TO USE: python data_miner.py <num_months>
"""

import sys
import time
import os
import requests
import sklearn
from sklearn.linear_model import LinearRegression
import warnings
import urllib3
from bs4 import BeautifulSoup
warnings.filterwarnings('ignore')
import numpy as np


def main():
    start = time.time()
    num_months = validate_user_input()
    stocks = get_symbols()
    russell_ret,last_date = get_russell_returns()
    rf_ret = get_rf_rate(last_date) # takes about 16 seconds to complete this task
    interact(num_months,stocks,russell_ret,rf_ret)
    end = time.time()
    total = end - start
    print("program took: {} sec(s)".format(round(total,5)))


# parses the treasury.gov page and retrieves daily yield curve rates by scraping data off the webpage
# returns a list of monthly yield curve rates based on the IEX dates for our stock returns
def get_rf_rate(last_date):
    url = "https://www.treasury.gov/resource-center/data-chart-center/interest-rates/pages/TextView.aspx?data=yieldAll"
    http = urllib3.PoolManager()
    page = http.request('GET', url)
    soup = BeautifulSoup(page.data)
    all_entries = soup.find_all('tr')
    all_entries = all_entries[len(all_entries)-1500:len(all_entries)-6] # getting around 6 years into past
    last_date = last_date[5:7]+"/"+last_date[2:4] # update date to valid format
    monthly_ret = get_monthly_rf_rate(all_entries, last_date)
    return monthly_ret


# takes in a list of entries which are table rows and gets the date and return from them
# only starts saving returns once we reach the ealiest date we need from IEX
# returns a list of monthly risk free returns
def get_monthly_rf_rate(all_entries, last_date):
    updates_entries = []
    found_date = False # boolean to find whether we have found the start date of when we want to collect risk free data
    for entry in all_entries:
        entry = str(entry)
        entry = entry.replace(">"," ").replace("<"," ").split(" ")
        date = entry[7][0:3]+entry[7][6:8] # removing the day from the date
        ret = entry[12] # yield for this day
        if ret == "NA": # there is no yield for 1mo. tbills during this date
            ret = 0
        else:
            ret = float(ret) / 100

        if found_date == False: # we are too far in the past
            if date == last_date: # we reached the date we need
                found_date = True 

        if found_date == True: # we are now saving information
            updates_entries.append({"date":date,"close":ret})

    monthly_ret = turn_to_monthly(updates_entries)
    print("finished scraping internet for risk free returns")
    return monthly_ret


# gets and validates user input, determines number of months for getting betas - 60 month max due to IEX constraints
# note - it is possible that there aren't 60 months of records for a given stock
# returns the number of months
def validate_user_input():
    try: # try to get the number of days from user arg
        num_months = sys.argv[1]
        try: # check if the user input is a number
            num_months = int(num_months)
        except:
            print("defaulted to 60 b/c you didn't input a valid number")
            num_months = 60
    except: # defaults to 60
        num_months = 60
        print("defaulted to 60 b/c you didn't input a number")

    if num_months < 1 or num_months > 60:
        num_months = 60
        print("defaulted to 60 b/c you didn't input a valid number")

    return num_months


# reads in a text file of symbols - deliniated by \n - assumes file is in same dir. and called stocks.txt
# returns a list of the stock symbols as strings
def get_symbols():
    stocks = []
    with open("./stocks.txt") as file:
        lines = file.readlines()
        for line in lines:
            line = line.strip("\n")
            stocks.append(line)
    return stocks


# takes in a list of daily returns and gets the last close price for any given month
# returns a list of monthly returns
def turn_to_monthly(daily_returns):
    date_lis = []
    monthly_ret = []

    for ret in daily_returns:
        if ret["date"] not in date_lis: # new month, so save first close price
            date_lis.append(ret["date"])
            monthly_ret.append(ret["close"])
        else: # same month so update close price
            monthly_ret[-1] = ret["close"]

    return monthly_ret


# gets the monthly returns for the russell 2000 (IWM) for the last 5 years
# returns a list of returns along with the earliest month for our returns
def get_russell_returns():
    returns = []
    resp = requests.get("https://api.iextrading.com/1.0/stock/IWM/chart/5y")
    if resp.status_code == 200: # there is no problem
        resp_json = resp.json()
        for day in resp_json:
            day_date = day["date"][0:7] # only saving year and month of date
            returns.append({"date":day_date,"close":day["close"]}) # saving date and close price info for all days
    else:
        print("Could not fetch russell 2000 data.")
        raise Exception("No russell, no analysis lol, iex may be down.")

    last_date = returns[0]["date"] # date of the ealiest we need a rf rate for
    returns = turn_to_monthly(returns)
    return returns,last_date


# Interacts with the IEX server, pulling the returns for each company and computing the betas/alpha/idiosyncratic vol.
# Saves all of the information in a csv file along with their ticker names
def interact(num_months,stocks,russell_ret,rf_ret):
    print("starting to compute the values for each stock")
    with open("stock_summary.csv","w") as file: # to write to file
        file.write("Ticker,Beta,Alpha,Idiosyncratic risk,Months Used\n")
        for ticker in stocks:
            resp = requests.get("https://api.iextrading.com/1.0/stock/{}/chart/5y".format(ticker))
            if resp.status_code == 200: # there is no problem 
                resp_json = resp.json()
                comp_returns = turn_to_monthly([{"date":day["date"][0:7],"close":day["close"]} for day in resp_json]) # get monthly ret.
                comp_beta,comp_alpha,sub_len,idio_risk = compute_beta(comp_returns,russell_ret,num_months,rf_ret) # get the beta value
                comp_beta = round(comp_beta,7)
                comp_alpha = round(comp_alpha,7)
                file.write(ticker+","+str(comp_beta)+","+str(comp_alpha)+","+str(idio_risk)+","+str(sub_len)+"\n") # writing values to file
            else:
                print("Could not get the data for {}".format(ticker))
                file.write(ticker+": NO BETA COMPUTED, invalid ticker for IEX\n")


# computes idiosyncratic risk 
def get_idiosyncratic_risk(beta,company_ret,market_ret):
    idio_risk = np.asscalar(np.sqrt(np.var(company_ret)-((beta**2)*np.var(market_ret))))
    return idio_risk


# Returns the beta given the russell monthly returns and the company monthly returns
# only uses data up the the min number of company returns or the user input for num_months
# returns the beta score as a float
def compute_beta(comp_returns,russell_ret,num_months,rf_ret):
    sub_comp,sub_russ,subset_len = get_subset_returns(comp_returns,russell_ret,num_months,rf_ret)
    reg = LinearRegression().fit(sub_russ,sub_comp) # variance in company ret. explained by model using market ret. as predictor
    comp_coef = reg.coef_ # single coefficient is the beta
    comp_alpha = reg.intercept_ # alpha is the intercept
    idio_risk = get_idiosyncratic_risk(comp_coef,sub_comp,sub_russ)
    return np.asscalar(comp_coef),np.asscalar(comp_alpha),subset_len,idio_risk


# makes sure that the russell returns and company returns used are the same length
# returns subsets of both lists of returns as numpy arrays
def get_subset_returns(comp_returns,russell_ret,num_months,rf_ret):
    if num_months > len(comp_returns): # there aren't enough monthly returns in IEX for company
        subset_len = len(comp_returns)
    else: # user input is valid number of months
        subset_len = num_months

    sub_comp = comp_returns[len(comp_returns)-subset_len:] # get correct subset of company data
    sub_russ = russell_ret[len(russell_ret)-subset_len:] # taking most recent chunk OF NON-PERCENTAGE RETURNS
    rf_ret = rf_ret[len(rf_ret)-subset_len:] # getting subset of risk free returns
    
    # Getting percentage returns:
    per_comp = [(sub_comp[i+1]-sub_comp[i])/sub_comp[i] for i in range(len(sub_comp)-1)]
    per_russ = [(sub_russ[i+1]-sub_russ[i])/sub_russ[i] for i in range(len(sub_russ)-1)]
    # getting risk free rate
    per_comp = [per_comp[i]-rf_ret[i] for i in range(len(per_comp))] # getting risk free returns for company
    per_russ = [per_russ[i]-rf_ret[i] for i in range(len(per_russ))] # getting risk free returns for market
    # creating numpy arrays
    per_comp = np.array(per_comp)
    per_russ = np.array(per_russ)
    per_comp.shape = (subset_len-1,1) # reshaping to 2D array
    per_russ.shape = (subset_len-1,1)
    
    return per_comp,per_russ,subset_len


if __name__=="__main__":
    main()