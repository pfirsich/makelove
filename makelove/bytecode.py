import os
import subprocess
import zipfile
import base64

def compile_file(love_binary, data, filename):
    # Compile a single .lua file to bytecode using love.
    # To support this, we have a folder 'love-luac' that will be recognized as 'game' by love
    compiler = os.path.join(os.path.dirname(__file__), 'love-luac')
    compile_args = [love_binary, compiler]
    proc = subprocess.Popen(compile_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    # (Binary) data is base64 encoded to work around the fact that lua opens stdin/stdout in text mode on windows,
    # which would break the bytecode
    out = proc.communicate(input=base64.b64encode(data))
    if proc.returncode == 0:
        return base64.b64decode(out[0])
    print('Failed to compile {}: {}'.format(filename, out[0]))
    return data


def create_compiled_lovezip(love_binary, love_file_path_in, love_file_path_out):
    # Create a new zip with all .lua files converted to bytecode
    with zipfile.ZipFile(love_file_path_in, 'r') as zip_in:
        with zipfile.ZipFile(love_file_path_out, 'w') as zip_out:
            zip_out.comment = zip_in.comment # preserve the comment
            for item in zip_in.infolist():
                data = zip_in.read(item.filename)
                if item.filename.endswith('.lua'):
                    data = compile_file(love_binary, data, item.filename)
                zip_out.writestr(item, data)

