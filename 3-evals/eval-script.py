import pandas

from eval_list import eval_qna
from main import answer_question

class bcolors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'

for test in eval_qna:
    question = test['question']
    # expected_answer = test['expected_answer']

    try:
        answer = answer_question(question)
        # print(answer.to_string(index=False))
        try:
            expected_answer = test['expected_answer']
            if isinstance(answer, str):
                if answer == expected_answer:
                    print(f"{bcolors.OKGREEN}[/] Eval passed for question: '{question}'")
                else:
                    print(f"{bcolors.FAIL}[/] Eval failed for question: '{question}'. Expected: {expected_answer}, got: {answer}")
            else:
                pandas.testing.assert_frame_equal(answer, expected_answer)
                print(f"{bcolors.OKGREEN}[/] Eval passed for question: '{question}'")
        except KeyError:
            pass
    except ValueError as e:
        if str(e) == test['expected_exception']:
            print(f"{bcolors.OKGREEN}[/] Eval passed for question: '{question}'")
        else:
            print(f"{bcolors.FAIL}[/] Eval failed for question: '{question}'. Expected exception: {test['expected_exception']}, got: {str(e)}")
    except Exception as e:
        print(f"{bcolors.FAIL}[/] Eval failed for question: '{question}' with an error:")
        print(e)
