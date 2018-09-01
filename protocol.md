
## 1: Preparation

The Evaluator prepares the submission.

Invoked with:

    evaluator.prepare(cie)
    
can invoke:

    cie.set_challenge_parameters(dict)
    cie.set_challenge_file(basename, data, description)
    
    
## 2: The solution runs

Invoked with:

    solution.run(cis)

can invoke:

    cie.get_challenge_parameters()
    
    cie.set_solution_output_dict(dict)
    cie.set_solution_output_file(basename, data, description)
    
## 3: The evaluator scores:

Invoked with:

    evaluator.score_submission(cie)
    
The evaluator must set the scores:

    cie.get_solution_output_dict()
    cie.get_solution_output_file(basename)
    cie.get_solution_output_files() -> (basename -> description)
    
    cie.set_score(name, value, description)
