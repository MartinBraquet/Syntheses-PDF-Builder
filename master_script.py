import subprocess
import os
import re
import shlex
import fnmatch
import yaml

# Absolute path to the config file
CONFIG_FILE_LOCATION = '/mnt/d/SynthesesEPL/Syntheses/src'  # Linux Location
# CONFIG_FILE_LOCATION = 'D:\SynthesesEPL\Syntheses\src'  # Windows Location
CONFIG_FILE_NAME = 'config.yml'
CONFIG_FILE_FULL_PATH = os.path.abspath(os.path.join(CONFIG_FILE_LOCATION, CONFIG_FILE_NAME))


# Tested on Windows/Linux only and Python 3.4 or above
def main():
    # Portable thing for DEVNULL
    # https://stackoverflow.com/a/11270665/6149867
    try:
        from subprocess import DEVNULL  # py3k
    except ImportError:
        DEVNULL = open(os.devnull, 'wb')

    # load the config file
    with open(CONFIG_FILE_FULL_PATH, 'r') as stream:
        try:
            document = yaml.load(stream)
            stream.close()

            # to handle some tricky path cases
            syntheses_folder = os.path.abspath(os.path.join(CONFIG_FILE_LOCATION, document['input_base']))
            out_folder = os.path.abspath(os.path.join(CONFIG_FILE_LOCATION, document['output_base']))

            # mapping dictionary to make life simpler
            mapping_dictionary, default_argument_mapping = build_dictionary(document)

            # find files that matches default file format : courseLabel-courseId-typeFile.tex
            file_list = find_latex_files(syntheses_folder)  # I suppose here the src folder is not empty

            print("Starting building all the files")
            # retrieve the data provided by the name build_command
            builder_array = [build_command(file, out_folder, mapping_dictionary) for file in file_list]
            # filter : take only the files that have a not empty translated_properties
            filtered_array = [(basename, dirname, translated_properties)
                              for basename, dirname, translated_properties in builder_array if translated_properties]

            # create the new folder and prevent a racing condition
            directories_array = [translated_properties['folderPath']
                                 for basename, dirname, translated_properties in filtered_array]
            create_all_directories(directories_array)

            # bulk build stuff
            for basename, dirname, translated_properties in filtered_array:
                try:
                    sub_command = translated_properties['buildCommand']
                    subprocess.call(sub_command, shell=True, cwd=dirname, stdout=DEVNULL)
                    print("\t The following file was successfully builded : " + basename)
                except subprocess.CalledProcessError as e:
                    print("Cannot compile %s into a pdf" % basename)
            print("End of building step")

            # clean task : I don't like to have aux , log , synctex.gz files on the output so time to clean it
            print("Remove the temp files produced by latex : aux log synctex.gz")
            try:
                # remove_temp_files(out_folder)
                print("Remove to be fixed")
            except subprocess.CalledProcessError as e:
                print("Cannot remove the temp files produced by pdflatex")

        except yaml.YAMLError as exc:
            print(exc)
        except AttributeError as err:
            print(err)


# Cross plateform find command that matches default file format : courseLabel-courseId-typeFile.tex
def find_latex_files(syntheses_folder):
    matches = []
    for root, dirnames, filenames in os.walk(syntheses_folder):
        for filename in fnmatch.filter(filenames, '*.tex'):
            matches.append(os.path.join(root, filename))
    return matches


def remove_temp_files(output_folder):
    remove_tuple = (".bcf", ".gnuplot", ".tdo", ".xml", ".aux", ".log", ".synctex.gz")
    for root, dirnames, filenames in os.walk(output_folder):
        for file in filenames:
            if (file.endswith(x) for x in remove_tuple):
                os.remove(os.path.join(root, file))
    print("Files removed")


def build_command(file, out_folder, mapping_dictionary):
    basename = os.path.basename(file)
    dirname = os.path.dirname(file)

    # filename common pattern extractor ; to handle most case
    common_pattern = re.compile('(?P<course_label>\w+)-(?P<course_id>\w+)-(?P<type>\w+)(?P<rest>.+)?.tex')
    result = common_pattern.match(basename)

    # dictionaries for custom purpose
    name_dictionary = mapping_dictionary['name']
    quadri_dictionary = mapping_dictionary['quadri']
    option_dictionary = mapping_dictionary['option']
    type_dictionary = mapping_dictionary['type']

    # where I keep the result
    translated_properties = {}

    # if match regex, we have data for renaming and moving stuff
    if result:
        course_label = result.group('course_label')
        course_id = result.group('course_id')
        resource_type = result.group('type')
        string_rest = result.group('rest')  # can be None
        quadri_pattern = re.compile('.+q(?P<quadri>[1-8]).+')
        quadri_result = quadri_pattern.match(dirname)

        # to extract option and code, I do this
        option_code_pattern = re.compile('(?P<option>[a-zA-Z]+)(?P<code>[0-9]+)')
        option_code_result = option_code_pattern.match(course_id)

        # create a easy to use object with the values extracted and mapped with dictionaries
        translated_properties.update({
            'name': name_dictionary[course_label] if course_label in name_dictionary else None,
            'type': type_dictionary[resource_type] if resource_type in type_dictionary else None,
            'courseLabel': course_id,  # Just in case I needed the full courseLabel
        })

        if option_code_result:
            option = option_code_result.group('option')
            code = option_code_result.group('code')
            translated_properties['option'] = option_dictionary[option] if option in option_dictionary else None
            translated_properties['code'] = code if code is not None else None,

        # Presque sur d'avoir toujours un result mais bon, faut mieux checker que debug
        if quadri_result:
            quadri = quadri_result.group('quadri')
            quadri = int(quadri)  # To int
            translated_properties['quadri'] = quadri
            translated_properties['quadri-folder'] = quadri_dictionary[quadri] if quadri in quadri_dictionary else None

        if string_rest:
            # pattern à supporter à l'avenir : -Sol comme -2015-Janvier-All-Sol
            rest_pattern = re.compile('-(?P<year>[0-9]+)-(?P<month>[a-zA-Z]+)-(?P<minmaj>All|Mineure|Majeure)')
            rest_result = rest_pattern.match(string_rest)

            if rest_result:
                translated_properties['year'] = rest_result.group('year')
                translated_properties['month'] = rest_result.group('month')
                translated_properties['minmaj'] = rest_result.group('minmaj')

        translated_properties = generate_folder_name(translated_properties, basename, out_folder)

    return basename, dirname, translated_properties


# a useful way to have all the useful mappings in config
def build_dictionary(document):
    # default mapping
    # key : 'quadri' , value : (1-8)
    # key : 'name' , value : ['advSecu', 'advalgo',..]
    # key : 'option' , value : ['FSAB', 'AUCE',..]
    # key : 'code' , value : [1031, 1101, 1102,...] (not useful for me)
    # key : 'type' , value : ['exercises', 'errata', 'formulaire', 'mcq', 'notes', 'summary']
    # not useful for me : 'code', 'sol', 'num'
    default_argument_mapping = document['clients'][0]['arguments']
    temp_mapping = document['clients'][0]['output']['parameters'][0]  # temp var to simplify my life ^^

    # merged type ; to have all the types declared in this config yml
    custom_type = dict()
    custom_type.update(document['clients'][0]['output']['parameters'][1]['mapping'])
    custom_type.update(document['clients'][1]['output']['parameters'][1]['mapping'])

    # make a more simpler dictionary because I don't hard yml stuff
    mapping_dictionary = dict(
        [
            (temp_mapping['parameters'][0]['key']['arg'], temp_mapping['parameters'][0]['mapping']),  # quadri
            (temp_mapping['parameters'][1]['key']['arg'], temp_mapping['parameters'][1]['mapping']),  # option
            (temp_mapping['parameters'][4]['arg'], default_argument_mapping[temp_mapping['parameters'][4]['arg']]),
            # code
            (temp_mapping['parameters'][5]['key']['arg'], temp_mapping['parameters'][5]['mapping']),  # name
            (document['clients'][0]['output']['parameters'][1]['key']['arg'],  # type
             custom_type),
            ('year', document['clients'][1]['arguments']['year']),  # year
            ('month', document['clients'][1]['arguments']['month']),  # month
            ('minmaj', document['clients'][1]['arguments']['minmaj']),  # minmaj
            ('sol', default_argument_mapping['sol'])  # sol
        ]
    )
    return mapping_dictionary, default_argument_mapping


# Generate the path and the build command in one time
# Warning : ugly if cascade code coming XD
def generate_folder_name(translated_properties, basename, out_folder):
    # if the algo cannot guess the rightful path, put it in the default folder
    if not check_dictionary(translated_properties, 'quadri-folder'):
        translated_properties['folderPath'] = out_folder
    else:
        translated_properties['folderPath'] \
            = os.path.abspath(os.path.join(out_folder, translated_properties['quadri-folder']))
        if check_dictionary(translated_properties, 'option'):
            translated_properties['folderPath'] \
                = os.path.abspath(os.path.join(translated_properties['folderPath'], translated_properties['option']))
            if check_dictionary(translated_properties, 'quadri'):
                translated_properties['folderPath'] \
                    = os.path.abspath(os.path.join(translated_properties['folderPath'],
                                                   'Q' + str(translated_properties['quadri'])))
                if check_dictionary(translated_properties, 'courseLabel') and check_dictionary(translated_properties,
                                                                                               'name'):
                    folder_name = translated_properties['courseLabel']
                    if check_dictionary(translated_properties, 'name'):
                        folder_name += ' - ' + translated_properties['name']
                    # Because some crazy guys put invalid chars inside name XD
                    folder_name = sanitize_folder_name(folder_name)
                    translated_properties['folderPath'] \
                        = os.path.abspath(os.path.join(translated_properties['folderPath'], folder_name))
                    if check_dictionary(translated_properties, 'type'):
                        translated_properties['folderPath'] \
                            = os.path.abspath(os.path.join(translated_properties['folderPath'],
                                                           translated_properties['type']))
                        if check_dictionary(translated_properties, 'year') \
                                and check_dictionary(translated_properties, 'month'):
                            translated_properties['folderPath'] \
                                = os.path.abspath(os.path.join(translated_properties['folderPath'],
                                                               translated_properties['year'] + ' - ' +
                                                               translated_properties['month']))

    # add the build command to this
    # Secure the bash command to prevent quote issues
    sub_build_command = 'pdflatex -interaction nonstopmode -output-format {} -output-directory {} {}'
    translated_properties['buildCommand'] = sub_build_command.format(
            'pdf',
            shlex.quote(translated_properties['folderPath']),
            shlex.quote(basename)
    )

    return translated_properties


# custom function to check a dict has a key and it value if not empty
def check_dictionary(my_dict, my_property):
    if my_property in my_dict.keys():
        if my_dict[my_property] is None:
            return False
        else:
            return True
    else:
        return False


# See https://docs.python.org/3/library/os.html#os.makedirs for more detail
def create_all_directories(directories):
    for path in directories:
        if not os.access(path, os.F_OK):
            os.makedirs(path, exist_ok=True)


# https://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx
def sanitize_folder_name(string):
    invalid_char = ["<", ">", ":", "\"", "/", "\\", "|", "?", "*"]
    result = string
    for i_char in invalid_char:
        result = result.replace(i_char, ' ')
    return result


if __name__ == "__main__": main()
