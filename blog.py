from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import  wraps

#Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı açmaya yetkiniz yok","danger")
            return redirect(url_for("login"))
    return decorated_function


# Register Form
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min=4,max=25)])
    user_name = StringField("Kullanıcı Adı",validators=[validators.Length(min=5,max=35)])
    email = StringField("Email Adresi",validators=[validators.Email("Bu bir email değildir")])
    password = PasswordField("Şifre:",validators=[
        validators.DataRequired("Şifre Giriniz"),
        validators.EqualTo(fieldname="confirm",message="Parola Uyuşmuyor")
    ])
    confirm = PasswordField("Parola doğrula")

class LoginForm(Form):
    username = StringField("Kullanıcı Adınız: ")
    password = PasswordField("Şifreniz: ")

class ArticleForm(Form): 
    title = StringField("Başlık Adınız: ",validators=[validators.DataRequired("Veri Giriniz..."),validators.Length(min=6)])
    content = TextAreaField("İçerik Giriniz: ",validators=[validators.DataRequired("Veri Giriniz..."),validators.Length(min=125)])

app = Flask(__name__)
app.secret_key = "ybblog"
app.config["MYSQL_HOST"] = "localhost" # mysql in bağlı olduğu yer
app.config["MYSQL_USER"] = "root" # mysql deki hesabın adı default olarak root gelir
app.config["MYSQL_PASSWORD"] = "" # mysql deki hesabın şifresi default olarak boş gelir
app.config["MYSQL_DB"] = "ybblog" # db adı
app.config["MYSQL_CURSORCLASS"] = "DictCursor" # verileri [{}] bu hale geitrdik
mysql = MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")
@app.route("/about")
def about():
    return render_template("about.html")

# article detail
@app.route("/article/<string:id>") # id alma
def detail(id):
    cursor = mysql.connection.cursor()
    result = cursor.execute("Select * from articles where id = %s ",(id,))
    if result > 0 :
        data = cursor.fetchone()
        print(data)
        return render_template("article.html",data=data)
    else:
        flash("Böyle bir makale bulunmuyor","danger")
        return render_template("article.html")
# Add Article
@app.route("/addarticle",methods=["GET","POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form) 
    if request.method == "POST" and form.validate(): 
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        cursor.execute("insert into articles values(default,%s,%s,%s,default)",(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Ekleme Başarılı","success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html",form=form)


# Articles
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    result =  cursor.execute("SELECT * FROM articles")
    if result > 0 :
        data = cursor.fetchall()
        return render_template("articles.html",articles=data)
    else:
        flash("Herhangi Bir Makale Bulunamadı....","danger")
        return render_template("articles.html")

# LocalHost Run

# Register
@app.route("/register",methods= ["GET","POST"])
def register():
   form = RegisterForm(request.form)
   if request.method == "POST" and form.validate():
       name = form.name.data
       user_name = form.user_name.data
       email = form.email.data
       password = sha256_crypt.encrypt(form.password.data)
       cursor = mysql.connection.cursor()
       cursor.execute("Insert into users values(default,%s,%s,%s,%s)",(name,email,user_name,password))
       mysql.connection.commit()
       cursor.close()
       flash("Kayıt Başarılı","success")

       return redirect(url_for("login"))
   else:
       return render_template("register.html",form=form)
# Login

@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password = form.password.data
        cursor = mysql.connection.cursor()
        result =  cursor.execute("Select * From users Where username = %s",(username,)) # True ise 0 dan büyük döncek
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password,real_password):
                flash("Giriş Başarılı...","success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Hatalı Şifre...","danger")
                return redirect(url_for("login"))

        else:
            flash("Böyle Bir Kullanıcı Mevcut Değil...","danger")
            return redirect(url_for("login"))
    else:
        return render_template("login.html",form=form)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    result = cursor.execute("Select * From articles where author = %s",(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")


# Delete and Edit

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    result = cursor.execute("select * from articles where author = %s and id = %s",(session["username"],id))
    if result > 0:
        cursor.execute("Delete From articles where id = %s",(id,))
        mysql.connection.commit()
        flash("Başarıyla Silindi","success")
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir veri yok veya yetkiniz bulunmuyor","danger")
        return redirect(url_for("index"))

@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def edit(id):
    if request.method == "POST":
        form = ArticleForm(request.form)
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        cursor.execute("Update articles set title = %s , content = %s where id = %s",(title,content,id))
        mysql.connection.commit()
        flash("Güncelleme Başarılı","success")
        return redirect(url_for("dashboard"))
    else:
        cursor = mysql.connection.cursor()
        result = cursor.execute("select * from articles where author = %s and id = %s",(session["username"],id))
        if result > 0:
            data = cursor.fetchone()
            form = ArticleForm()
            form.title.data = data["title"]
            form.content.data = data["content"]
            return render_template("edit.html",form=form)
        else:
            flash("Böyle bir veri yok veya yetkiniz bulunmuyor","danger")
            return redirect(url_for("index"))

# Search URL

@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword") #request içindeki form olan değişkenden name'i keyword olanı alma
        cursor = mysql.connection.cursor()
        result = cursor.execute("Select * from articles where title LIKE '%" + keyword + "%'")
        if result == 0:
            flash("Böyle Bir Makale Bulunamadı","danger")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles=articles)

if __name__ == "__main__": # eğer name == main se bu terminalden çalıştırılmıştır
    app.run(debug=True)
