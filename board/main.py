from flask import send_from_directory,Flask, url_for, jsonify , g , request, render_template, session, redirect, escape
import sqlite3, hashlib,os
from werkzeug.utils import secure_filename
DATABASE = './db/test.db'

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = set(['txt','pdf','png','jpg','jpeg','gif','zip'])
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    db= getattr(g, '_database', None)
    if db is None:
        db= g.database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None: db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
            db.commit()

def add_student(name,password,email,nname,pnum):
    hw = hashlib.sha224(password).hexdigest()
    sql = "INSERT INTO users (name,password,email,nname,pnum) VALUES('%s', '%s', '%s','%s','%s')" %(name,hw, email, nname, pnum)
    db = get_db()
    db.execute(sql)
    res=db.commit()
    return res

@app.route('/' , methods=['GET','POST'])
def index():
    if request.method =='GET':
        if 'user_id' in session:
            res=get_board()
            data = session['user_id']
            return render_template('index.html',data=data,users=res)
        else:
            return render_template('index.html')
    else:
            return render_template('index.html')
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method =='GET':
        if 'user_id' in session:
            return redirect(url_for('index'))
        else:
            return render_template('login.html')
    else:
        user_id = request.form.get('user_id')
        user_pw = request.form.get('user_pw')
        user_hw = hashlib.sha224(user_pw).hexdigest()
        ret = get_user(user_id,user_hw)
        if len(ret)!=0:
            session['user_id'] = ret[0]['name']
            return redirect(url_for('index'))
        else:
            return "<script>alert('id or password fail');history.go(-1)</script>"
@app.route('/user_edit', methods=['GET','POST'])
def user_edit():
    if request.method=='GET':
        if 'user_id' in session:
            name = session['user_id']
            res = edit_user(name)
            return render_template('user_edit.html',users=res)
        else:
            return redirect(url_for('index'))
    else:
        if 'user_id' in session:    
            user_pw=request.form.get('user_pw')
            user_email=request.form.get('user_email')
            user_nname=request.form.get('user_nname')
            user_pnum =request.form.get('user_pnum')
            data=overlap1(user_email,user_nname,user_pnum)
            if data:
                return "<script>alert('it already exist');history.go(-1)</script>"
            else:  
                user_update(user_pw,user_email,user_nname,user_pnum,session['user_id'])
            return redirect(url_for('index'))
        else:
            return redirect(url_for('index'))
def edit_user(name):
    sql = "select * from users where name='%s'" %(name)
    db=get_db()
    rv=db.execute(sql)
    res=rv.fetchall()
    return res
def user_update(password,email,nname,pnum,name):
    password=hashlib.sha224(password).hexdigest()
    sql = "update users set password='%s',email='%s', nname='%s', pnum='%s' where name='%s'" %(password,email,nname,pnum,name)
    db = get_db()
    db.execute(sql)
    res = db.commit()
    return res
@app.route('/user_delete', methods=['GET','POST'])
def user_delete():
    if request.method=='GET':
        if 'user_id' in session:
            res=edit_user(session['user_id'])
            return render_template('user_delete.html',users=res)
        else:
            return redirect(url_for('index'))
    else:
        if 'user_id' in session:
            user_pw=request.form.get('user_pw')
            user_hw=hashlib.sha224(user_pw).hexdigest()
            res=edit_user(session['user_id'])
            if res[0]['password']!=user_hw:
                return "<script>alert('password wrong');history.go(-1)</script>"
            else:
                delete_user(session['user_id'],user_hw)
                session.pop('user_id',None)
                return redirect(url_for('index'))
        else:
            return redirect(url_for('index'))

def delete_user(name,password):
    sql="delete from users where name='%s' and password='%s'"%(name,password)
    db=get_db()
    db.execute(sql)
    res=db.commit()
    return res
@app.route('/board_modify/<idx>' , methods=['GET','POST'])
def board_update(idx):
    if request.method=='GET':
        if 'user_id' in session:
            res=get_view(idx)
            if res[0]['name']!=session['user_id']:
                return "<script>alert('nono');history.go(-1)</script>"
            else:
                res = board_edit(idx)
                return render_template('board_modify.html',data=res)
        else:
            return redirect(url_for('add_user'))
    else:
        board_title=request.form.get('board_title')
        board_content=request.form.get('board_content')
        if len(board_title)==0:
            return "<script>alert('input title');history.go(-1)</script>"
        else:
            update_board(idx,board_title,board_content)
            return redirect(url_for('index'))
@app.route('/board_delete/<idx>', methods=['GET'])
def board_delete(idx):
    if request.method=='GET':
        if 'user_id' in session:
            res =get_view(idx)
            res1= reply_content_chk(idx)
            if res[0]['name']!=session['user_id']:
                return "<script>alert('nono'); history.go(-1)</script>"
            elif res[0]['name']==session['user_id'] and len(res1)!=0:
                return "<script>alert('nono'); history.go(-1)</script>"
            else:
                delete_board(idx)
                return redirect(url_for('index'))
        else:
            return redirect(url_for('index'))
def reply_content_chk(idx):
    sql = "select content from reply where idx_r='%s'" %(idx)
    db = get_db()
    rv=db.execute(sql)
    res =rv.fetchall()
    return res
def update_board(idx,board_title,board_content):
    sql = "update board SET title='%s',content='%s', dt=current_timestamp where idx='%s'" %(board_title,board_content,idx)
    db = get_db()
    db.execute(sql)
    res = db.commit()
    return res
def delete_board(idx):
    sql = "delete from board where idx='%s'" %(idx)
    db  = get_db()
    db.execute(sql)
    res = db.commit()
    return res
def board_edit(idx):
    sql = "select * from board where idx='%s'" %(idx)
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall()
    return res
def reply_chk(idx,name):
    sql = "select 1 from reply where idx='%s' and name='%s'" %(idx,name)
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall() 
    return res
def reply_edit(content,idx_r,idx):
    sql = "update reply set content='%s' where idx_r='%s' and idx='%s'" %(content,idx_r,idx)
    db = get_db()
    db.execute(sql)
    res = db.commit()
    return res
@app.route('/board_view/<idx_r>/reply/<idx>',methods=['GET','POST'])
def reply_view(idx_r,idx):
    if request.method=='GET':
        if 'user_id' in session:
            res=reply_chk(idx,session['user_id'])
            if res:
                res=reply_enroll1(idx_r,idx)
                return render_template('reply_update.html',res=res)
            else:
                return "<script>alert('nono');history.go(-1)</script>"
    else:
        reply_content=request.form.get('reply_content')
        reply_edit(reply_content,idx_r,idx)
        return redirect(url_for('board_view',idx=idx_r))
@app.route('/board_view/<idx_r>/reply_delete/<idx>', methods=['GET','POST'])
def reply_delete(idx_r,idx):
    if request.method=='GET':
        if 'user_id' in session:
            res=reply_chk(idx,session['user_id'])
            if res:
                print idx_r,idx
                delete_reply(idx_r,idx)
                return redirect(url_for('board_view',idx=idx_r))
            else:
                return "<script>alert('nono');history.go(-1)</script>"
        else:
            redirect(url_for('index'))

def delete_reply(idx_r,idx):
    sql = "delete from reply where idx_r='%s' and idx='%s'" %(idx_r,idx)
    db=get_db()
    rv=db.execute(sql)
    res=db.commit()
    return res
@app.route('/board_view/<idx>', methods=['GET','POST'])
def board_view(idx):
    if request.method=='GET':
        if 'user_id' in session:
            res=get_view(idx)
            #res1=get_reply(session['user_id'])
            res2=reply_enroll(idx)
            data=session['user_id']
            return  render_template('board_view.html',res=res,res2=res2,data=data)
        else:
            return redirect(url_for('index'))
    else:
        if 'user_id' in session:
            res = get_view(idx)
            reply_content=request.form.get('reply_content')
            reply_update(session['user_id'], reply_content,idx)
            return redirect(url_for('board_view', idx=idx))
def reply_enroll(idx):
    sql = "select * from reply where idx_r='%s'" %(idx)   
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall()
    return res
def reply_enroll1(idx_r,idx):
    sql = "select * from reply where idx_r='%s' and idx='%s'" %(idx_r,idx)
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall()
    return res

def reply_update(name,content,idx):
    sql = "insert into reply(name,content,idx_r) values('%s','%s','%s')" %(name,content,idx)
    db  = get_db()
    db.execute(sql)
    res=db.commit()
    return res
def get_reply(name):
    sql = "select *from reply where name='%s'" %(name)
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall()
    return res
def get_users():
    sql = 'SELECT * FROM users'
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall()
    return res

def get_board():
    sql = 'SELECT * from board order by idx desc'
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall()
    return res
def get_view(idx):
    sql = "SELECT idx,name,title,content,dt,upload  from board where idx='%s'" %(idx)
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall()
    return res

@app.route('/logout', methods=['GET','POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

def get_user(name,password):
    sql = 'select * from users where name="%s" and password="%s"'%(name,password)
    db = get_db()
    rv = db.execute(sql)
    res =rv.fetchall()
    return res
@app.route('/secret', methods=['GET','POST'])
def secret():
    if request.method =='GET':
        #return render_template('secret.html')
        data = session['user_email']
        return render_template('mailto.html',data=data)
       # return session['user_email']
@app.route('/add', methods =['GET','POST'])
def add_user():
    if request.method == 'GET':
        res = get_users()
        return render_template('add.html',users=res)
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        user_pw = request.form.get('user_pw')
        user_email = request.form.get('user_email')
        user_nname = request.form.get('user_nname')
        user_pnum  = request.form.get('user_pnum')
        data = overlap(user_id,user_email,user_nname,user_pnum)
        if data:
            return "<script>alert('it already exist');history.go(-1)</script>"
        else:
            add_student(user_id,user_pw,user_email,user_nname,user_pnum)
        return redirect(url_for('index'))
def overlap(name,email,nname,pnum):
    sql = "SELECT 1 FROM users where name='%s' or email='%s' or nname='%s' or pnum='%s'" %(name,email,nname,pnum)
    db  = get_db()
    rv  = db.execute(sql)
    res = rv.fetchall()
    return res
def overlap1(email,nname,pnum):
    sql = "select 1 from users where email='%s' or nname='%s' or pnum='%s'" %(email,nname,pnum)
    db  = get_db()
    rv  = db.execute(sql)
    res = rv.fetchall()
    return res
@app.route('/board_write', methods =['GET','POST'])
def board_write():
    if request.method =='GET':
        if 'user_id' in session:
            res1 = session['user_id']
            return render_template('board_write.html',data=res1)
        else:
            return redirect(url_for('index'))
    else:
        board_title =   request.form.get('board_title')
        board_content = request.form.get('board_content')
        if len(board_title) == 0:
            return "<script>alert('input title');history.go(-1)</script>"
        else :
            if 'file' not in request.files:
                return ('no file1')
            f = request.files['file']
            if f and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                f.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
                add_board(board_title,board_content,session['user_id'],filename)
                #return redirect(url_for('uploaded_file',filename=filename))
                return redirect(url_for('index'))
            else:
                return 'nono'
        return redirect(url_for('index'))
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)
def add_board(title,content,name,file_name):
    sql = "INSERT into board(title,content,name,upload) values('%s','%s','%s','%s')" %(title,content,session['user_id'],file_name)
    db = get_db()
    rv = db.execute(sql)
    res = db.commit()
    return res
def modify_board(content,idx):
    sql = "update board set content='%s' where idx='%s'" %(content,idx)
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall()
    return res
app.secret_key = 'asaa'
if __name__=='__main__':

    app.run(debug=True, host='0.0.0.0', port=8001)



