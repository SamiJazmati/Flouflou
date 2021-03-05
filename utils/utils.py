import subprocess
import time


def template_to_file(
    templateFile,
    values,
    cwd,
    deleteBackup=False,
    destination=None,
    newTemplateFileName=None,
):
    [
        subprocess.check_output(
            ['sed', '-i', '_origin', f's#{originalValue}#{newValue}#g', templateFile],
            cwd=cwd,
        )
        for originalValue, newValue in values.items()
    ]
    if deleteBackup:
        subprocess.check_output(
            ['rm', '-f', f'{templateFile}_origin'],
            cwd=cwd,
        )
    if destination:
        if newTemplateFileName:
            subprocess.check_output(
                ['mv', f'{cwd}/{templateFile}', f'{destination}/{newTemplateFileName}']
            )
        else:
            subprocess.check_output(
                ['mv', f'{cwd}/{templateFile}', f'{destination}/{templateFile}']
            )
        subprocess.check_output(['mv', f'{templateFile}_origin', templateFile], cwd=cwd)
    return


def templates_to_files(
    templateFiles,
    values,
    cwd,
    deleteBackup=False,
    destination=None,
):
    return [
        template_to_file(
            templateFile=templateFile,
            values=values,
            cwd=cwd,
            deleteBackup=deleteBackup,
            destination=destination,
        )
        for templateFile in templateFiles
    ]


def rename_file_or_folder(originalName, newName, cwd):
    return subprocess.check_output(['mv', originalName, newName], cwd=cwd)


def wait_until(condition, expected, timeout, period, *args, **kwargs):
    timeoutExceeded = time.time() + timeout
    while time.time() < timeoutExceeded:
        if condition(*args, **kwargs) == expected:
            return True
        time.sleep(period)
    return False
