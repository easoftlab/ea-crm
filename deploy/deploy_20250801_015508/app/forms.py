from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, DateField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from wtforms.widgets import TextArea

class LeadForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=2, max=128)])
    company_website = StringField('Company Website', validators=[DataRequired(), Length(max=256)])
    country = StringField('Country', validators=[DataRequired(), Length(max=64)])
    state = StringField('State', validators=[Optional(), Length(max=64)])
    industry = StringField('Industry', validators=[DataRequired(), Length(max=64)])
    source = StringField('Source', validators=[Optional(), Length(max=64)])
    timezone = StringField('Timezone', validators=[Optional(), Length(max=16)])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Add Lead')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField('First Name', validators=[Optional(), Length(max=80)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class UserProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    first_name = StringField('First Name', validators=[Optional(), Length(max=80)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField('Update Profile')

class ComprehensiveUserProfileForm(FlaskForm):
    # Basic Information
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=80)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    
    # Personal Information
    date_of_birth = DateField('Date of Birth', validators=[DataRequired()])
    nid_number = StringField('NID Number', validators=[DataRequired(), Length(max=50)])
    profile_image = FileField('Profile Image', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')
    ])
    
    # Contact Information
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    emergency_phone = StringField('Emergency Phone', validators=[DataRequired(), Length(max=20)])
    
    # Address Information
    current_address = TextAreaField('Current Address', validators=[DataRequired()])
    permanent_address = TextAreaField('Permanent Address', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    state_province = StringField('State/Province', validators=[DataRequired(), Length(max=100)])
    postal_code = StringField('Postal Code', validators=[DataRequired(), Length(max=20)])
    country = StringField('Country', validators=[DataRequired(), Length(max=100)])
    
    # Family Information
    father_name = StringField('Father\'s Name', validators=[DataRequired(), Length(max=100)])
    mother_name = StringField('Mother\'s Name', validators=[DataRequired(), Length(max=100)])
    
    # Additional Information
    blood_group = SelectField('Blood Group', choices=[
        ('', 'Select Blood Group'),
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-')
    ], validators=[DataRequired()])
    
    marital_status = SelectField('Marital Status', choices=[
        ('', 'Select Marital Status'),
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed'),
        ('Separated', 'Separated')
    ], validators=[DataRequired()])
    
    emergency_contact_name = StringField('Emergency Contact Name', validators=[DataRequired(), Length(max=100)])
    emergency_contact_relationship = StringField('Emergency Contact Relationship', validators=[DataRequired(), Length(max=50)])
    
    submit = SubmitField('Update Profile')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    new_password2 = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class UserManagementForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField('First Name', validators=[Optional(), Length(max=80)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=80)])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active')
    submit = SubmitField('Save User') 