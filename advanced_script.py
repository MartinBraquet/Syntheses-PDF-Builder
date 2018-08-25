import subprocess
import os
import platform
import re
import fnmatch
import yaml

# Absolute path to the config file
CONFIG_FILE_LOCATION = '/mnt/d/SynthesesEPL/Syntheses/src'  # Linux Location
# CONFIG_FILE_LOCATION = 'D:\SynthesesEPL\Syntheses\src'  # Windows Location
CONFIG_FILE_NAME = 'config.yml'
CONFIG_FILE_FULL_PATH = os.path.abspath(os.path.join(CONFIG_FILE_LOCATION, CONFIG_FILE_NAME))

# type of folder expected
TYPE_FILE = 'summary'


# Tested on Linux only and Python 3.6 or above with TYPE_FILE = 'summary'
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

            # mapping dictionnary
            mapping_course_name = document['clients'][0]['output']['parameters'][0]['parameters'][5]['mapping']

            # find files that matches default file format : courseLabel-courseId-typeFile.tex
            file_list = find_files(syntheses_folder)

            # filename part extractor ; to rename the output pdf files
            pattern = re.compile('(\w+)-(\w+)-(\w+)(.+)?.tex')

            print("Starting building all the files")
            for file in file_list:
                # run command from another cwd : https://stackoverflow.com/a/43851335/6149867
                basename = os.path.basename(file)
                dirname = os.path.dirname(file)
                sub_build_command = ['pdflatex',
                                     '-interaction nonstopmode',
                                     '-output-directory ' + out_folder,
                                     '-output-format pdf']
                result = pattern.match(basename)

                # if match regex, rename the output file
                if result:
                    course_label = result.group(1)
                    course_id = result.group(2)

                    # if the mapped value exists in mapping_course_name
                    if course_label in mapping_course_name:
                        full_name = mapping_course_name[course_label]
                        sub_build_command.append('--jobname="' + course_id + ' - ' + full_name + ' - ' + TYPE_FILE + '"')
                try:
                    sub_command = ' '.join(sub_build_command) + ' ' + basename
                    subprocess.call(sub_command, shell=True, cwd=dirname, stdout=DEVNULL)
                    print("\t The following file was successfully builded : " + basename)
                except subprocess.CalledProcessError as e:
                    print("Cannot compile %s into a pdf" % basename)
            print("End of building step")

            # clean task
            # I don't like to have aux , log , synctex.gz files on the output so time to clean it
            print("Remove the temp files produced by latex : aux log synctex.gz")
            try:
                remove_command = 'rm -f *.aux *.log *.synctex.gz'
                subprocess.Popen(remove_command, shell=True, cwd=out_folder, stdout=DEVNULL)
            except subprocess.CalledProcessError as e:
                print("Cannot remove the temp files produced by pdflatex")

        except yaml.YAMLError as exc:
            print(exc)
        except AttributeError as err:
            print(err)


# Cross plateform find command that matches default file format : courseLabel-courseId-typeFile.tex
def find_files(syntheses_folder):
    if 'Windows' is platform.system():
        matches = []
        for root, dirnames, filenames in os.walk(syntheses_folder):
            for filename in fnmatch.filter(filenames, '*-*-' + TYPE_FILE + '.tex'):
                matches.append(os.path.join(root, filename))
        return matches
    else:
        find_latex_files = ['find', syntheses_folder, '-name "*-*-' + TYPE_FILE + '.tex"', '-type f']
        command = ' '.join(find_latex_files)
        stdout = subprocess.check_output(command, shell=True)
        # Save found files to list
        return stdout.decode().split()


if __name__ == "__main__": main()
