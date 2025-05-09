from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Account, Transaction, generate_bank_number
from sqlalchemy.orm import joinedload

# 创建主功能蓝图
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required # 必须登录后才能访问仪表盘

def dashboard():
    # current_user.accounts 来自 User.accounts 关系，列出该用户所有账户
    accounts = current_user.accounts
    # 将账户列表传给 dashboard.html 模板渲染
    return render_template('dashboard.html', accounts=accounts)

@main_bp.route('/open_account', methods=['GET', 'POST'])
@login_required
def open_account():
    if request.method == 'POST':
        # 从表单读取“账户名称”，若用户未填写则自动命名
        acc_name = request.form['name'] or f"账户{len(current_user.accounts)+1}"
        # 生成一个唯一的 16 位银行卡号
        bn = generate_bank_number()
        # 如果刚才生成的银行卡号已存在，则重新生成直到唯一
        while Account.query.filter_by(bank_number=bn).first():
            bn = generate_bank_number()
        # 构造新的 Account 实例，初始余额为 0.0
        new_acc = Account(user_id=current_user.id, name=acc_name, balance=0.0, bank_number=bn)

        db.session.add(new_acc)
        db.session.commit()

        flash('新账户创建成功。')
        # 创建成功后重定向回仪表盘，显示最新账户列表
        return redirect(url_for('main.dashboard'))
    # GET 请求渲染开户表单
    return render_template('open_account.html')

@main_bp.route('/account/<int:acc_id>')
@login_required
def view_account(acc_id):
    # 使用 joinedload 预加载 transactions 和它们的 other_account
    account = Account.query.options(
        joinedload(Account.transactions).joinedload(Transaction.other_account)
    ).get_or_404(acc_id)
    # 渲染账户详情页，模板中可直接访问 account.transactions 和 account.bank_number 等
    return render_template('account.html', account=account)


@main_bp.route('/deposit', methods=['POST'])
@login_required
def deposit():
    # 根据隐藏字段 acc_id 找到对应账户
    acc = Account.query.get_or_404(request.form['acc_id'])
    amount = float(request.form['amount'])
    # 增加余额
    acc.balance += amount
    # 记录一条存款交易
    db.session.add(Transaction(account_id=acc.id, t_type='Deposit', amount=amount))
    db.session.commit()

    flash('存款成功。')
    # 操作完成后回到该账户详情页
    return redirect(url_for('main.view_account', acc_id=acc.id))


@main_bp.route('/withdraw', methods=['POST'])
@login_required
def withdraw():
    acc = Account.query.get_or_404(request.form['acc_id'])
    amount = float(request.form['amount'])
    # 提示并阻止超额取款
    if amount > acc.balance:
        flash('余额不足。')
    else:
        # 扣减余额并记录交易
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

    # 读取并验证转账金额
    amount = request.form.get('amount', type=float)
    error = None
    if dst is None:
        error = f'目标银行卡号 {to_bn} 不存在。'
    elif amount is None or amount <= 0:
        error = '请输入大于 0 的有效金额。'
    elif amount > src.balance:
        error = '账户余额不足。'

    # 若有任一校验失败，提示并返回到账户详情
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