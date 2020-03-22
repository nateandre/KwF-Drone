""" 
Creates a likelihood model for sex probability given a particular first name. For use in predicting the probability that a given author of a publication is a certain sex. Likelihoods are stored for individual years, along with a total count being calculated. This is to allow the lookup for a particular year if the DOB, or estimate, can be guessed. The total count is the default if the name is not found in the year, or no name is found. Data is stored in the following format: {"year":{"Name":"f":<count>,"m":<count>}}. The dataset used goes from late 1800s to 2014.

Author: Nathaniel Andre
"""

import csv
import json

def main():
    clean_data()
        

def clean_data(data_path="./data/NationalNames.csv",out_path="./data/likelihoods.json"):
    """ Saves a dict of counts of sex for all names, aggregated and by year, as a json file.
    args:
        data_path: path to the csv file holding all baby names
        out_path: path to save the output file
    """
    fname = open(data_path)
    reader = csv.reader(fname)
    next(reader) # skip the header
    global_data_dict = {"total":{}}

    for row in reader:
        name = row[1].lower()
        year = row[2]
        sex = row[3].lower()
        count = int(row[4])

        if year not in global_data_dict.keys(): # first occurance of year
            global_data_dict[year] = {}

        if name not in global_data_dict[year].keys(): # first occurance of name for year
            if sex == "f":
                global_data_dict[year][name] = {"f":count,"m":0}
            else: # male
                global_data_dict[year][name] = {"f":0,"m":count}
        else:
            global_data_dict[year][name][sex] += count

        if name not in global_data_dict["total"].keys(): # first occurance of name in aggregated data
            if sex == "f":
                global_data_dict["total"][name] = {"f":count,"m":0}
            else: # male
                global_data_dict["total"][name] = {"f":0,"m":count}
        else:
            global_data_dict["total"][name][sex] += count

    with open(out_path,"w+") as out_fname:
        json.dump(global_data_dict,out_fname)

    data_path.close()


if __name__=="__main__":
    main()
