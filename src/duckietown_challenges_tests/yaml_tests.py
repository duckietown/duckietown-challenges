from comptests import comptest, run_module_tests
# from duckietown_challenges.yaml_utils import interpret_yaml_string
#
# example = """\
# !!omap
# - status: failed
# - msg: "the message"
# - scores: {}
# - stats: {}
# """
#
#
# @comptest
# def read1():
#     x = interpret_yaml_string(example)
#     print(x)
#     assert isinstance(x, dict), type(x)


if __name__ == '__main__':
    run_module_tests()
