"""
This file defines actions, i.e. functions the URLs are mapped into
The @action(path) decorator exposed the function at URL:

    http://127.0.0.1:8000/{app_name}/{path}

If app_name == '_default' then simply

    http://127.0.0.1:8000/{path}

If path == 'index' it can be omitted:

    http://127.0.0.1:8000/

The path follows the bottlepy syntax.

@action.uses('generic.html')  indicates that the action uses the generic.html template
@action.uses(session)         indicates that the action uses the session
@action.uses(db)              indicates that the action uses the db
@action.uses(T)               indicates that the action uses the i18n & pluralization
@action.uses(auth.user)       indicates that the action requires a logged in user
@action.uses(auth)            indicates that the action requires the auth object

session, db, T, auth, and tempates are examples of Fixtures.
Warning: Fixtures MUST be declared with @action.uses({fixtures}) else your app will result in undefined behavior
"""

from py4web import action, request, abort, redirect, URL
from yatl.helpers import A
from .common import db, session, T, cache, auth, logger, authenticated, unauthenticated
import datetime
import json
from .models import add_or_update_score

@unauthenticated()
@action('index')
@action.uses(auth, 'index.html')
def index():
    user = auth.get_user()
    # message = T("Hello {first_name}".format(**user))
    message = 'Hello World'
    return dict(message=message)

@authenticated
@action('teacher_broadcasts', method='POST')
# @action.uses('index.html')
def teacher_broadcasts():
    content = request.POST['content']
    answer = request.POST['answer']
    merit = int(request.POST['merit'])
    effort = int(request.POST['effort'])
    attempts = int(request.POST['attempts'])
    topic_id = 0 #int(request.POST['topic_id'])
    tag = request.POST['tag']
    filename = request.POST['filename']
    exact_answer = 1 if request.POST['exact_answer']=='True' else 0
    # print(request.query)
    # return dict(message='')
    rows = db(db.tag.topic_description == tag).select()
    if len(rows)==0:
        tag_id = db.tag.insert(topic_description=tag)
    else:
        for row in rows:
            tag_id = row.id
            break
    pid = db.problem.insert(teacher_id=1, problem_description=content, answer=answer, filename=filename, merit=merit, effort=effort, attempts=attempts, topic_id=topic_id, tag=tag_id, problem_uploaded_at=datetime.datetime.now(), exact_answer=exact_answer, active=1)
    # print(content)
    # print(answer)
    return 'Content copied to white boards.'


@authenticated
@action('ask', method='POST')
# @action.uses('index.html')
def ask():
    path = request.environ['PATH_INFO'].split('/')[1]
    url = '%s://%s/%s/' % (request.environ['wsgi.url_scheme'], request.environ['HTTP_HOST'], path)
    return url
    

@unauthenticated
@action('student_gets', method='POST')
def student_gets():
    boards = []
    for row in db(db.problem.active==1).select():
        boards.append({'Content': row.problem_description, 'Filename': row.filename, 'Type': 'Question'})
    return json.dumps(boards)

@unauthenticated
@action('student_shares', method='POST')
def student_shares():
    content = request.POST['content']
    filename = request.POST['filename']
    answer = request.POST['answer']
    priority = int(request.POST['priority'])
    uid = request.POST['uid']
    prob = None
    verdict = ""
    for row in db(db.problem.filename==filename).select():
        prob = row
        break
    scoring_msg = "Your submission will be looked at soon."
    msg = ""
    complete = False
    if prob is not None:
        if prob.active != 1:
            msg = "Problem is no longer active. But the teacher will look at your submission."
        else:
            attempts = db.attempt(problem_id=prob.id, student_id=uid)
            if attempts is None:
                db.attempt.insert(problem_id=prob.id, student_id=uid, remaining_attempt=prob.attempts)
                attempts = db.attempt(problem_id=prob.id, student_id=uid)

            if attempts is not None and attempts.remaining_attempt==0:
                return "This is not submitted because either you have reached the submission limit or your solution was previously graded correctly."
            db(db.attempt.id==attempts.id).update(remaining_attempt=attempts.remaining_attempt-1)
            if priority < 2 :
                if attempts.remaining_attempt<=3:
                    msg = " You have " + str(attempts.remaining_attempt-1)+" attempt(s) left."
            

            correct_answer = prob.answer
            if answer != "":
                if correct_answer == answer:
                    scoring_msg = add_or_update_score("correct", prob.id, uid, 1, -1)
                    print(attempts)
                    db(db.attempt.id == attempts.id).update(remaining_attempt=0)
                    complete = True
                    verdict = "correct"
                elif prob.exact_answer == 1:
                    scoring_msg = add_or_update_score("incorrect", prob.id, uid, 1, -1)
                    complete = True
                    verdict = "incorrect"
                else:
                    scoring_msg = "Answer appears to be incorrect. It will be looked at. "
            
            if complete == True:
                db.submission.insert(problem_id=prob.id, student_id=uid, student_code=content, submission_category=priority, code_submitted_at=datetime.datetime.now(), completed=datetime.datetime.now(), looked_at = datetime.datetime.now(), verdict=verdict)
            else:
                db.submission.insert(problem_id=prob.id, student_id=uid, student_code=content, submission_category=priority, code_submitted_at=datetime.datetime.now())
            db.commit()
        if verdict == "correct":
            return scoring_msg
        return scoring_msg+msg


@authenticated
@action('teacher_gets_queue', method='POST')
def teacher_gets_queue():
    submissions = []
    for sub in db((db.submission.completed == None)&(db.submission.looked_at==None)).select(orderby=db.submission.code_submitted_at):
        submissions.append({'Sid': sub.id, 'Uid': sub.student_id, 'Pid': sub.problem_id, 'Content': sub.student_code, 'Filename': db.problem[sub.problem_id].filename, 'Priority': sub.submission_category, 'Name': db.student[sub.student_id].name})
    return json.dumps(submissions)

@authenticated
@action('teacher_gets', method='POST')
def teacher_gets():
    index = int(request.POST['index'])
    priority = int(request.POST['priority'])
    selected = {}
    workingsubs = db((db.submission.completed == None)&(db.submission.looked_at==None)).select(orderby=db.submission.code_submitted_at)
    if index >= 0:
        sub = workingsubs[index]
        selected = {'Sid': sub.id, 'Uid': sub.student_id, 'Pid': sub.problem_id, 'Content': sub.student_code, 'Filename': db.problem[sub.problem_id].filename, 'Priority': sub.submission_category, 'Name': db.student[sub.student_id].name}
        db.submission(sub.id).update(looked_at=datetime.datetime.now())
    elif priority > 0:

        for sub in workingsubs:
            if sub.priority == priority:
                selected = {'Sid': sub.id, 'Uid': sub.student_id, 'Pid': sub.problem_id, 'Content': sub.student_code, 'Filename': db.problem[sub.problem_id].filename, 'Priority': sub.submission_category, 'Name': db.student[sub.student_id].name}
                db.submission(sub.id).update(looked_at=datetime.datetime.now())
                break
    else:
        first_sub_w_priority = [-1, -1, -1]
        for i in range(len(workingsubs)):
            p = workingsubs[i].priority
            if first_sub_w_priority[p] == -1:
                first_sub_w_priority[p] = i
        for i in range(len(first_sub_w_priority)-1, -1, 0):
            if first_sub_w_priority[i] != -1:
                j = first_sub_w_priority[i]
                sub = workingsubs[j]
                selected = {'Sid': sub.id, 'Uid': sub.student_id, 'Pid': sub.problem_id, 'Content': sub.student_code, 'Filename': db.problem[sub.problem_id].filename, 'Priority': sub.submission_category, 'Name': db.student[sub.student_id].name}
                db.submission(sub.id).update(looked_at=datetime.datetime.now())
                break
    return selected


@authenticated
@action('teacher_puts_back', method='POST')
def teacher_puts_back():
    sid = int(request.POST['sid'])
    db.submission(sid).update(looked_at=None)
    return "Submission has been put back into the queue."
