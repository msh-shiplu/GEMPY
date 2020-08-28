"""
This file defines the database models
"""

from .common import db, Field
from pydal.validators import *

import datetime
### Define your table below
#
# db.define_table('thing', Field('name'))
#
## always commit your models to avoid problems later
#
# db.commit()
#
def create_tables():
    db.define_table('student', Field('user_id', type='reference auth_user'), redefine=True)
    db.define_table('teacher', Field('user_id', type='reference auth_user'), redefine=True)
#     db.define_table('course', Field('course_id', notnull=True), Field('course_name'), Field('semester'), Field('Year', type='integer'), Field('teacher_id', type='reference teacher'))
    db.define_table('attendance', Field('student_id', type='reference student', notnull=True), Field('attendance_at', type='datetime'))
    db.define_table('tag', Field('topic_description', unique=True))
    db.define_table('problem', Field('teacher_id', type='reference teacher'), Field('problem_description', type='text'), Field('answer', type='text'),\
     Field('filename'), Field('merit', type='integer'), Field('effort', type='integer'), Field('attempts', type='integer'), Field('topic_id', type='integer'),\
     Field('tag', type='integer'), Field('problem_uploaded_at', type='datetime'), Field('exact_answer', type='integer'), Field('active', type='integer'), redefine=True) 
    db.define_table('submission', Field('problem_id', type='reference problem'), Field('student_id', type='reference student'), Field('student_code', type='text'), Field('submission_category',\
         type='integer'), Field('code_submitted_at', type='datetime'), Field('completed', type='datetime'), Field('verdict'), Field('looked_at', type='datetime'), redefine=True)
    db.define_table('score', Field('problem_id', type='reference problem'), Field('student_id', type='reference student'), Field('teacher_id', type='reference teacher'), Field('score', type='integer'),\
         Field('graded_submission_number', type='integer'), Field('score_given_at', type='datetime'))
    db.define_table('feedback', Field('teacher_id', type='reference teacher'), Field('feedback', type='text'), Field('feedback_given_at', type='datetime'), Field('submission_id', type='reference submission'))
    
    db.define_table('attempt', Field('problem_id', type='reference problem'), Field('student_id', tyep='reference student'), Field('remaining_attempt', type='integer'))

    db.define_table('board_queue', Field('student_id', type='reference student'), Field('content_id', type='integer'), Field('content_type'), Field('added_at', type='datetime'), redefine=True) # content_type: problem, feedback
    db.commit()


def add_or_update_score(decision, problem_id, student_id, teacher_id, partial_credits):
     mesg = ""
     
     score_id, current_points, current_attempts, current_tid = 0, 0, 0, 0

     row = db.score(problem_id=problem_id, student_id=student_id)
     if row is not None:
          score_id, current_points, current_attempts, current_id = row.id, row.score, row.graded_submission_number, row.teacher_id

     merit, effort = 0, 0
     row = db.problem(problem_id)
     if row is not None:
          merit = row.merit
          effort = row.effort
     points, teacher = 0, teacher_id
     if decision == "correct":
          points = merit
          mesg = "Answer is correct."
     else:
          if partial_credits < merit:
               points = partial_credits
          else:
               points = effort
          
          if points < current_points:
               points = current_points
          
          mesg = "Answer is incorrect."
     if score_id == 0:
          db.score.insert(problem_id=problem_id, student_id=student_id, teacher_id=teacher_id, score=points, graded_submission_number=current_attempts+1, score_given_at=datetime.datetime.now())
     else:
          db(db.score.id==score_id).update(teacher_id=teacher_id, score=points, graded_submission_number=current_attempts+1)
     
     return mesg
