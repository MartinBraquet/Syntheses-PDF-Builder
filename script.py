import subprocess
import os

# Absolute path to this folder root
SYNTHESES_FOLDER = '/mnt/d/SynthesesEPL/Syntheses'
# Absolute path to out folder
OUT_FOLDER = '/mnt/d/SynthesesEPL/Drive'

# type of folder expected
TYPE_FILE = 'summary'


# Linux only XD
def main():

    # Portable thing for DEVNULL
    # https://stackoverflow.com/a/11270665/6149867
    try:
        from subprocess import DEVNULL  # py3k
    except ImportError:
        DEVNULL = open(os.devnull, 'wb')


    # thanks https://docs.python.org/2/library/subprocess.html#replacing-shell-pipeline
    # find part
    find_latex_files = ['find', SYNTHESES_FOLDER, '-name "*.tex"', '-type f']
    grep_filter = 'grep -e \/' + TYPE_FILE + '\/'

    # command part
    command = ' '.join(find_latex_files) + ' | ' + grep_filter
    stdout = subprocess.check_output(command, shell=True)

    # Save found files to list
    file_list = stdout.decode().split()

    build_command = ['pdflatex',
                     '-interaction nonstopmode',
                     '-output-directory ' + OUT_FOLDER,
                     '-output-format pdf']

    print("Starting building all the files")
    for file in file_list:
        # run command from another cwd : https://stackoverflow.com/a/43851335/6149867
        basename = os.path.basename(file)
        dirname = os.path.dirname(file)
        try:
            sub_command = ' '.join(build_command) + ' ' + basename
            subprocess.call(sub_command, shell=True, cwd=dirname, stdout=DEVNULL)
        except subprocess.CalledProcessError as e:
            print("Cannot compile %s into a pdf" % basename)
    print("End of building step")

    # clean task
    # I don't like to have aux , log , synctex.gz files on the output so time to clean it

    print("Remove the temp files produced by latex : aux log synctex.gz")
    try:
        remove_command = 'rm -f *.aux *.log *.synctex.gz'
        subprocess.Popen(remove_command, shell=True, cwd=OUT_FOLDER, stdout=DEVNULL)
    except subprocess.CalledProcessError as e:
        print("Cannot remove the temp files produced by pdflatex")


if __name__ == "__main__": main()

