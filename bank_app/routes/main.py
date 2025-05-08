from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Account, Transaction, generate_bank_number
from sqlalchemy.orm import joinedload

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
        acc_name = request.form['name'] or f"账户{len(current_user.accounts)+1}"
        bn = generate_bank_number()
        while Account.query.filter_by(bank_number=bn).first():
            bn = generate_bank_number()
        new_acc = Account(user_id=current_user.id, name=acc_name, balance=0.0, bank_number=bn)
        db.session.add(new_acc)
        db.session.commit()
        flash('新账户创建成功。')
        return redirect(url_for('main.dashboard'))
    return render_template('open_account.html')

@main_bp.route('/account/<int:acc_id>')
@login_required
def view_account(acc_id):
    account = Account.query.options(
        joinedload(Account.transactions).joinedload(Transaction.other_account)
    ).get_or_404(acc_id)
    return render_template('account.html', account=account)


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
    # 取出来源账户（按内部 ID）
    from_acc_id = request.form.get('from_acc', type=int)
    src = Account.query.get_or_404(from_acc_id)

    # 按银行卡号查找目标账户
    to_bn = request.form.get('to_bn', type=str)
    dst = Account.query.filter_by(bank_number=to_bn).first()

    # 验证输入
    amount = request.form.get('amount', type=float)
    error = None
    if dst is None:
        error = f'目标银行卡号 {to_bn} 不存在。'
    elif amount is None or amount <= 0:
        error = '请输入大于 0 的有效金额。'
    elif amount > src.balance:
        error = '账户余额不足。'

    if error:
        flash(error)
        return redirect(url_for('main.view_account', acc_id=src.id))

    # 执行转账
    src.balance -= amount
    dst.balance += amount

    # 记录交易：转出和转入
    txn_out = Transaction(
        account_id=src.id,
        t_type='Transfer Out',
        amount=amount,
        other_account_id=dst.id
    )
    txn_in = Transaction(
        account_id=dst.id,
        t_type='Transfer In',
        amount=amount,
        other_account_id=src.id
    )
    db.session.add_all([txn_out, txn_in])
    db.session.commit()

    flash(f'成功向银行卡号 {to_bn} 转账 {amount} 元。')
    return redirect(url_for('main.view_account', acc_id=src.id))