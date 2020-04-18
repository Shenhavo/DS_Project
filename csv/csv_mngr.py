import csv
from py_files import global_consts

class CsvMngr:
    '''
    handles reading and writing from CSV files
    '''
    def __init__(self, a_path):
        self.path = a_path
        self.list = []
        with open(self.path + '/config.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
            for row in reader:
                self.list.append(row)

    def get_param(self, a_key, a_type=None):
        """
        get_param:
        a_key is a string containing the param name
        a_type is one of the known types of objects in global_consts
         """
        retval = None
        for Dict in self.list:
            try:
                if Dict['param'] == a_key:
                    if a_type in global_consts.TYPES_L:
                        if a_type == bool:
                            retval = Dict['value'].lower() in global_consts.True_L
                    else:
                        retval = Dict['value']
                    break
            except KeyError: # ignore
                pass
            except ValueError:
                print("ValueError")
                retval = a_key
                pass
            except Exception as e:
                raise e
        return retval