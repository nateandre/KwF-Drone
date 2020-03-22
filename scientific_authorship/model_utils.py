"""
Loads in and uses the likelihood model to determine whether a name is more likely to be male or female. For year prompts, the aggregate dict will be used if the name could not be found in the year dict.

Author: Nathaniel Andre
"""

import json
import pandas as pd
import numpy as np
import warnings
import time
warnings.simplefilter("ignore")

def main():
    fname = "Lacertilia 1990-99.csv"
    out_fname = fname.split(".")[0]+" Updated.csv"
    print(fname)
    run_prediction_model_from_file(fname,out_fname)
    #get_entry_for_name("NA")


def run_prediction_model_from_file(fname,out_fname):
    """ Runs the prediction model with a excel file
    """
    afile = open("./data/likelihoods.json")
    data_dict = json.load(afile)
    csv = pd.read_csv(fname)
    name_columns = [name for name in csv.columns if name[0:2]=="AU" and "FN" in name] # columns w/ first & middle names
    for column_name in name_columns:
        start = time.time()
        name_number = column_name.split()[0] # e.g. AU1
        name_sex_column = name_number+" SEX" # column name to fill in sex
        name_confidence_column = name_number+" CONFIDENCE" # column name to fill in confidence
        names = csv[column_name] # all the names for this num. author
        for name_i in range(len(names)):
            name = names[name_i]
            if type(name) != str: # this is an empty cell, skip
                continue

            name_split = name.replace("-"," ").split() # list of names/initials, based on SPLIT RULE
            most_common_name_prob,most_common_sex = get_most_common_sex(name_split,data_dict)
            if most_common_sex != "":
                csv[name_sex_column][name_i] = most_common_sex # setting index of sex score
                csv[name_confidence_column][name_i] = most_common_name_prob # setting index of confidence score
            
            else: # late addition to differentiate unknown names
                csv[name_sex_column][name_i] = "Unknown"

        print(column_name,round(time.time()-start,4),"sec")

    csv.to_csv(out_fname) # save the pandas dframe as a csv


def get_most_common_sex(name_split,data_dict):
    """ Takes in a list of names (FName,MiddleName,Initials,Etc.) and returns the most common name w/ prob. of name.
        Out of a list of first/middle names, returns the sex of the name w/ the highest likelihood of being one sex or another. Defaults to "" if no name was found. Incorporates the data from ALL years. Ignores initials.
    
    """
    max_conf = 0
    max_name = ""
    max_sex = ""
    for name in name_split:
        if len(name)!=1 and "." not in name and not (len(name)<=3 and name==name.upper()): # not a initial
            name = name.lower()
            sex,prob = get_prediction_no_year(data_dict,name)
            if sex != None: # name w/ probability was found
                if prob > max_conf: # this name has a higher likelihood
                    max_conf = prob
                    max_name = name
                    max_sex = sex

    return max_conf,max_sex


def get_entry_for_name(name):
    """ Meant for testing purposes, returns the f/m split data dict for a given name.
    """
    afile = open("./data/likelihoods.json")
    data_dict = json.load(afile)
    try:
        data = data_dict["total"][name.lower()]
        print(data)
    except:
        print("no entry.")


def get_prediction_no_year(data_dict,name):
    """ Returns the most likely sex,prob or None,None
    """
    if name in data_dict["total"].keys():
        return maximum_female_or_male(data_dict["total"][name])
    else:
        return None,None
    

def maximum_female_or_male(info_dict):
    """ Returns either female or male, depending on the one with the highest count & returns probability.
    """
    m = info_dict["m"]
    f = info_dict["f"]
    total = f + m
    if f >= m:
        return "female",f/total
    else:
        return "male",m/total


def get_prediction_with_year(data_dict,name,year):
    """ Returns the most likely sex, or "Couldn't discern". Used when year is included as a variable.
    """
    if name in data_dict[year].keys():
        return maximum_female_or_male(data_dict[year][name])
    else:
        return get_prediction_no_year(data_dict,name)


""" Currently removed functionality: Allows running of the prediction model from terminal.
def run_prediction_model_locally():
    afile = open("./data/likelihoods.json")
    data_dict = json.load(afile)
    print("At the prompt enter the name (required) follow by year (optional).")
    
    while True:
        prompt = input("Enter info: ")
        user_prompts = prompt.split()
        num_prompts = len(user_prompts)
        
        if num_prompts != 2 and num_prompts != 1:
            print("Invalid input.")
            continue

        if num_prompts == 2: # finding data for name,year input
            name,year = user_prompts
            if year not in data_dict.keys():
                print("Invalid year.")
                continue
            else:
                print(get_prediction_with_year(data_dict,name,year))

        else: # just the name was given
            name = user_prompts[0]
            print(get_prediction_no_year(data_dict,name))
"""

if __name__=="__main__":
    main()