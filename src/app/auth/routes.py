from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app.extensions import mail, get_db
from flask_login import current_user, login_user, login_required, logout_user

from . import auth_bp
from .utils import verify_otp, generate_otp, send_otp_email, is_valid_email, store_otp
from app.main.User import User

import random
from bson import ObjectId


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        otp = request.form.get('otp')

        if not email or not otp:
            return render_template('auth/login.html',
                                   error="Please enter your Email and verification code.")

        # Verify OTP
        if not verify_otp(email, otp):
            return render_template('auth/login.html',
                                   error="Verification is wrong or has already expired.")

        user = User.get_by_email(email)

        # No such user check
        if not user:
            flash("User not exist or not authorized", "error")
            return redirect(url_for('auth.login'))

        login_user(user)
        return render_template('home.html')

    return render_template('auth/login.html')


@auth_bp.route('/api/request_otp', methods=['POST'])
def api_request_otp():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify(success=False, message="Email field can't be empty")

    if not is_valid_email(email):
        return jsonify(success=False, message="Email format error")

    # Generate OTP and send mail
    otp = generate_otp()
    print("Sending OTP to: " + email)
    if send_otp_email(email, otp):
        store_otp(email, otp)
        return jsonify(success=True)
    else:
        return jsonify(success=False, message="Email sending failed")



@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    #flash('Logged out.', 'info')
    return redirect(url_for('main.home'))


@auth_bp.route('/whoami')
@login_required
def whoami():
    return jsonify({
        'user_id': str(current_user.user_id),
        'email': current_user.email,
        'username': current_user.username,
        'role': current_user.role.name,
        'access_level': current_user.access_level
    })


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # TODO: Register logics
    return render_template('register.html')

@auth_bp.route('/dev/init_organizations', methods=['POST'])
def init_organizations():
    db = get_db()

    # 获取所有可用银行账户
    bank_accounts = list(db.BankAccounts.find({}))
    if not bank_accounts:
        return jsonify({'error': 'No available bank accounts to assign'}), 400

    # 获取所有 O_CONVENER 用户
    conveners = list(db.Users.find({'role': 3}))  # 3 == O_CONVENER
    if not conveners:
        return jsonify({'error': 'No O_CONVENER users found'}), 404

    org_ids = []

    # 为每个 convener 创建 Organization
    for idx, convener in enumerate(conveners):
        selected_account = random.choice(bank_accounts)
        org_doc = {
            'longName': f'Organization {idx + 1}',
            'shortName': f'Org{idx + 1}',
            'convener': convener['_id'],
            'bankAccount': selected_account['_id'],  # 分配随机银行账户
            'email': convener.get('email', ''),
            'proofPath': f'/proofs/org{idx + 1}.pdf'
        }
        result = db.Organizations.insert_one(org_doc)
        org_ids.append(result.inserted_id)

        # 更新 convener 的 organization 字段
        db.Users.update_one(
            {'_id': convener['_id']},
            {'$set': {'organization': result.inserted_id}}
        )

    # 分配其他用户到随机 Organization
    others = list(db.Users.find({'role': {'$ne': 3}}))
    for user in others:
        assigned_org = random.choice(org_ids)
        db.Users.update_one(
            {'_id': user['_id']},
            {'$set': {'organization': assigned_org}}
        )

    return jsonify({
        'message': 'Organizations initialized and users assigned.',
        'organization_count': len(org_ids),
        'convener_count': len(conveners),
        'user_assigned_count': len(others)
    })