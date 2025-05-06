from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Account, Transaction

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def dashboard():
    accounts = current_user.accounts
    return render_template('dashboard.html', accounts=accounts)

@main_bp.route('/open_account', methods=['GET', 'POST'])
@login_required
def open_account():
    if request.method == 'POST':
        name = request.form['name'] or f"账户{len(current_user.accounts)+1}"
        acc = Account(user_id=current_user.id, name=name)
        db.session.add(acc)
        db.session.commit()
        flash('新账户创建成功。')
        return redirect(url_for('main.dashboard'))
    return render_template('open_account.html')

@main_bp.route('/account/<int:acc_id>')
@login_required
def view_account(acc_id):
    acc = Account.query.get_or_404(acc_id)
    if acc.user_id != current_user.id and not current_user.is_admin:
        flash('无权访问此账户。')
        return redirect(url_for('main.dashboard'))
    return render_template('account.html', account=acc)


@main_bp.route('/deposit', methods=['POST'])
@login_required
def deposit():
    acc = Account.query.get_or_404(request.form['acc_id'])
    amount = float(request.form['amount'])
    acc.balance += amount
    db.session.add(Transaction(account_id=acc.id, t_type='Deposit', amount=amount))
    db.session.commit()
    flash('存款成功。')
    return redirect(url_for('main.view_account', acc_id=acc.id))


@main_bp.route('/withdraw', methods=['POST'])
@login_required
def withdraw():
    acc = Account.query.get_or_404(request.form['acc_id'])
    amount = float(request.form['amount'])
    if amount > acc.balance:
        flash('余额不足。')
    else:
        acc.balance -= amount
        db.session.add(Transaction(account_id=acc.id, t_type='Withdraw', amount=amount))
        db.session.commit()
        flash('取款成功。')
    return redirect(url_for('main.view_account', acc_id=acc.id))


@main_bp.route('/transfer', methods=['POST'])
@login_required
def transfer():
    from_acc_id = request.form.get('from_acc', type=int)
    to_acc_id = request.form.get('to_acc', type=int)
    amount = request.form.get('amount', type=float)

    error = None
    src = Account.query.get(from_acc_id)
    dst = Account.query.get(to_acc_id)
    if src is None:
        error = f'来源账户 {from_acc_id} 不存在。'
    elif dst is None:
        error = f'目标账户 {to_acc_id} 不存在。'
    elif amount is None or amount <= 0:
        error = '请输入大于0的有效金额。'
    elif src.is_locked or dst.is_locked:
        error = '账户已锁定，无法转账。'
    elif amount > src.balance:
        error = '账户余额不足。'

    if error:
        flash(error)
        # 如果来源账户存在，则返回详情；否则返回仪表盘
        if src:
            return redirect(url_for('main.view_account', acc_id=src.id))
        return redirect(url_for('main.dashboard'))

        # 执行转账
    src.balance -= amount
    dst.balance += amount
    txn_out = Transaction(account_id=src.id, t_type='Transfer Out', amount=amount, other_account_id=dst.id)
    txn_in = Transaction(account_id=dst.id, t_type='Transfer In', amount=amount, other_account_id=src.id)
    db.session.add_all([txn_out, txn_in])
    db.session.commit()
    flash(f'成功向账户 {dst.name} 转账 {amount} 元。')
    return redirect(url_for('main.view_account', acc_id=src.id))