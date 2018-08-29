import shutil
import tempfile
import os

from duckietown_challenges import ConcreteChallengeInterface


def test1():

    d = tempfile.mkdtemp()
    input_dir = os.path.join(d, 'input_dir')
    os.makedirs(input_dir)
    output_dir = os.path.join(d, 'output_dir')
    os.makedirs(output_dir)
    temp_dir = os.path.join(d, 'temp_dir')
    os.makedirs(temp_dir)
    previous_step_dir = os.path.join(d, 'previous_step_dir')
    os.makedirs(previous_step_dir)

    contents = """

input_dir: {input_dir}
previous_step_dir: {previous_step_dir}
output_dir: {output_dir}
temp_dir: {temp_dir}
    
""".format(input_dir=input_dir, output_dir=output_dir,
           temp_dir=temp_dir, previous_step_dir=previous_step_dir)
    cf = os.path.join(d, 'config.yaml')

    with open(cf, 'w') as f:
        f.write(contents)


    ci = ConcreteChallengeInterface(cf)

    assert ci.get_input_dir() == input_dir
    assert ci.get_previous_step_dir() == previous_step_dir
    assert ci.get_output_dir() == output_dir
    assert ci.get_temp_dir() == temp_dir

    ci.write_environment_info()

    shutil.rmtree(d)
    print 'hi'
