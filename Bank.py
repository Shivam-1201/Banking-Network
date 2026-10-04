import mysql.connector
import sys
import os
import math
import time


HOST = os.environ.get("BANK_DB_HOST", "localhost")
USER = os.environ.get("BANK_DB_USER", "root")
PASSWORD = os.environ.get("BANK_DB_PASSWORD", "")
DBNAME = "bank_db"

MIN_BAL_SAVINGS = 500
MIN_BAL_CURRENT = 1000
HIGH_VALUE = 10000
DAILY_LIMIT = 50000
LOAN_RATE = 10.5
LOAN_MIN = 10000
FD_MIN = 1000
FD_PENALTY = 1.0

otps = {}


def connect_db():
    global mydb, cur
    mydb = mysql.connector.connect(host=HOST, user=USER, password='Shivam12#' )
    cur = mydb.cursor()
    cur.execute("CREATE DATABASE IF NOT EXISTS " + DBNAME)
    cur.execute("USE " + DBNAME)

    cur.execute("""CREATE TABLE IF NOT EXISTS customers (
        customer_id INT AUTO_INCREMENT PRIMARY KEY,
        full_name VARCHAR(100), email VARCHAR(100) UNIQUE,
        phone VARCHAR(10) UNIQUE, dob DATE, address VARCHAR(200),
        id_type VARCHAR(30), id_no VARCHAR(40),
        verified TINYINT DEFAULT 0)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS accounts (
        account_no BIGINT AUTO_INCREMENT PRIMARY KEY,
        customer_id INT, account_type VARCHAR(10),
        balance DOUBLE, pin_hash VARCHAR(20),
        status VARCHAR(10) DEFAULT 'ACTIVE',
        failed_attempts INT DEFAULT 0) AUTO_INCREMENT=1000000001""")

    cur.execute("""CREATE TABLE IF NOT EXISTS transactions (
        txn_id BIGINT AUTO_INCREMENT PRIMARY KEY,
        account_no BIGINT, txn_type VARCHAR(20), amount DOUBLE,
        balance_after DOUBLE, description VARCHAR(200),
        txn_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS loans (
        loan_id INT AUTO_INCREMENT PRIMARY KEY,
        account_no BIGINT, principal DOUBLE, rate DOUBLE,
        months INT, emi DOUBLE, outstanding DOUBLE,
        emis_paid INT DEFAULT 0, status VARCHAR(10) DEFAULT 'ACTIVE',
        start_date DATE)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS fixed_deposits (
        fd_id INT AUTO_INCREMENT PRIMARY KEY,
        account_no BIGINT, principal DOUBLE, rate DOUBLE,
        months INT, start_date DATE, maturity_date DATE,
        maturity_amount DOUBLE, status VARCHAR(10) DEFAULT 'ACTIVE')""")

    cur.execute("""CREATE TABLE IF NOT EXISTS cheques (
        cheque_no BIGINT AUTO_INCREMENT PRIMARY KEY,
        account_no BIGINT, payee_account BIGINT, amount DOUBLE,
        issue_date DATE, written_date DATE,
        status VARCHAR(12) DEFAULT 'UNUSED') AUTO_INCREMENT=500001""")
    mydb.commit()


def pause():
    time.sleep(1)


def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def read_int(msg):
    try:
        return int(input(msg).strip())
    except ValueError:
        print("Please enter a number.")
        return -1


def read_amount(msg):
    try:
        a = round(float(input(msg).strip()), 2)
    except ValueError:
        print("Invalid amount.")
        return 0
    if a <= 0:
        print("Amount must be positive.")
        return 0
    return a


def hash_pin(pin):

    h = 7
    for ch in pin:
        h = (h * 31 + ord(ch)) % 1000000007
    return str(h)


def valid_phone(p):
    return len(p) == 10 and p.isdigit()


def valid_email(e):
    return "@" in e and "." in e and e.find("@") > 0 and e.rfind(".") > e.find("@") + 1


def valid_pin(p):
    return p.isdigit() and 4 <= len(p) <= 6


def min_balance(acc_type):
    if acc_type == "SAVINGS":
        return MIN_BAL_SAVINGS
    return MIN_BAL_CURRENT


def make_otp(key, channel, target):
    code = str(int(time.time() * 1000000) % 900000 + 100000)
    otps[key] = (code, time.time() + 300)

    print("\n  [DEMO " + channel + " to " + target + "]  Your OTP is " + code + "\n")


def check_otp(key, code):
    if key in otps:
        real, expiry = otps[key]
        if time.time() <= expiry and real == code:
            del otps[key]
            return True
    return False


def otp_challenge(key, channel, target):
    make_otp(key, channel, target)
    for i in range(3):
        code = input("Enter " + channel + " OTP: ").strip()
        if check_otp(key, code):
            return True
        print("Wrong or expired OTP. Tries left:", 2 - i)
    return False


def step_up(phone, amt):

    if amt >= HIGH_VALUE:
        print("High value transaction - extra verification needed.")
        return otp_challenge("HV" + phone, "SMS", phone)
    return True


def get_account(acc_no):
    cur.execute("SELECT account_no, customer_id, account_type, balance, pin_hash, status, "
                "failed_attempts FROM accounts WHERE account_no=%s", (acc_no,))
    return cur.fetchone()


def save_txn(acc_no, ttype, amt, bal, desc):
    cur.execute("INSERT INTO transactions (account_no, txn_type, amount, balance_after, description) "
                "VALUES (%s,%s,%s,%s,%s)", (acc_no, ttype, amt, bal, desc))


def set_balance(acc_no, bal):
    cur.execute("UPDATE accounts SET balance=%s WHERE account_no=%s", (round(bal, 2), acc_no))


def move_money(src, dst, amt, d_out, d_in, t_out, t_in):
    a = get_account(src)
    b = get_account(dst)
    if a is None or b is None:
        return "Account not found."
    if a[5] != "ACTIVE" or b[5] != "ACTIVE":
        return "Account is not active."
    if a[3] - amt < min_balance(a[2]):
        return "Insufficient funds."
    new_src = round(a[3] - amt, 2)
    new_dst = round(b[3] + amt, 2)
    set_balance(src, new_src)
    set_balance(dst, new_dst)
    save_txn(src, t_out, amt, new_src, d_out)
    save_txn(dst, t_in, amt, new_dst, d_in)
    return "OK"


def create_account():
    print("\n===== OPEN NEW ACCOUNT =====")
    name = input("Full name: ").strip()
    email = input("Email: ").strip().lower()
    phone = input("Mobile number (10 digits): ").strip()
    dob = input("Date of birth (YYYY-MM-DD): ").strip()
    address = input("Address: ").strip()
    id_type = input("ID proof (Aadhaar/PAN/Passport): ").strip()
    id_no = input("ID number: ").strip()

    if name == "" or not valid_email(email) or not valid_phone(phone):
        print("Invalid name / email / phone.")
        return


    parts = dob.split("-")
    if len(parts) != 3 or not (parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit()):
        print("Invalid date format.")
        return
    if int(parts[1]) < 1 or int(parts[1]) > 12 or int(parts[2]) < 1 or int(parts[2]) > 31:
        print("Invalid date.")
        return
    this_year = int(time.strftime("%Y"))
    if this_year - int(parts[0]) < 18:
        print("You must be at least 18 years old.")
        return

    t = input("Account type (1-Savings, 2-Current): ").strip()
    if t == "1":
        acc_type = "SAVINGS"
    elif t == "2":
        acc_type = "CURRENT"
    else:
        print("Invalid type.")
        return

    cur.execute("SELECT customer_id FROM customers WHERE email=%s OR phone=%s", (email, phone))
    if cur.fetchone() is not None:
        print("Customer with this email or phone already exists.")
        return


    print("\nVerification 1 of 2 : Mobile number")
    if not otp_challenge("SU" + phone, "SMS", phone):
        print("Mobile verification failed. Account not created.")
        return
    print("Verification 2 of 2 : Email address")
    if not otp_challenge("SU" + email, "EMAIL", email):
        print("Email verification failed. Account not created.")
        return

    pin = input("Set a 4-6 digit PIN: ").strip()
    pin2 = input("Confirm PIN: ").strip()
    if pin != pin2 or not valid_pin(pin):
        print("PIN invalid or not matching.")
        return

    dep = read_amount("Opening deposit (min " + str(min_balance(acc_type)) + "): ")
    if dep < min_balance(acc_type):
        print("Opening deposit too low.")
        return

    try:
        cur.execute("INSERT INTO customers (full_name,email,phone,dob,address,id_type,id_no,verified) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,1)",
                    (name, email, phone, dob, address, id_type, id_no))
        cust_id = cur.lastrowid
        cur.execute("INSERT INTO accounts (customer_id, account_type, balance, pin_hash) "
                    "VALUES (%s,%s,%s,%s)", (cust_id, acc_type, dep, hash_pin(pin)))
        acc_no = cur.lastrowid
        save_txn(acc_no, "DEPOSIT", dep, dep, "Opening deposit")
        mydb.commit()
        print("\nAccount created successfully!")
        print("Account number :", acc_no)
        print("Account type   :", acc_type)
        print("Balance        : Rs.", dep)
    except mysql.connector.Error as e:
        mydb.rollback()
        print("Error:", e)


def login():
    print("\n===== LOGIN =====")
    acc_no = read_int("Account number: ")
    pin = input("PIN: ").strip()

    acc = get_account(acc_no)
    if acc is None:
        print("Account not found.")
        return None
    if acc[5] != "ACTIVE":
        print("Account is", acc[5], "- contact the bank.")
        return None

    if hash_pin(pin) != acc[4]:
        fails = acc[6] + 1
        if fails >= 3:
            cur.execute("UPDATE accounts SET failed_attempts=%s, status='FROZEN' WHERE account_no=%s",
                        (fails, acc_no))
            print("Wrong PIN. Account FROZEN after 3 wrong attempts.")
        else:
            cur.execute("UPDATE accounts SET failed_attempts=%s WHERE account_no=%s", (fails, acc_no))
            print("Wrong PIN. Attempts left:", 3 - fails)
        mydb.commit()
        return None

    cur.execute("UPDATE accounts SET failed_attempts=0 WHERE account_no=%s", (acc_no,))
    mydb.commit()

    cur.execute("SELECT full_name, phone FROM customers WHERE customer_id=%s", (acc[1],))
    name, phone = cur.fetchone()


    if not otp_challenge("LG" + phone, "SMS", phone):
        print("OTP verification failed.")
        return None
    print("\nWelcome,", name)
    return [acc_no, name, phone]


def show_balance(s):
    acc = get_account(s[0])
    print("\n" + acc[2], "account", s[0])
    print("Balance: Rs.", round(acc[3], 2))


def deposit(s):
    amt = read_amount("Deposit amount: ")
    if amt == 0:
        return
    acc = get_account(s[0])
    new_bal = round(acc[3] + amt, 2)
    set_balance(s[0], new_bal)
    save_txn(s[0], "DEPOSIT", amt, new_bal, "Cash deposit")
    mydb.commit()
    print("Deposited Rs.", amt, "| New balance: Rs.", new_bal)


def withdraw(s):
    amt = read_amount("Withdrawal amount: ")
    if amt == 0:
        return
    if not step_up(s[2], amt):
        return
    acc = get_account(s[0])
    cur.execute("SELECT IFNULL(SUM(amount),0) FROM transactions WHERE account_no=%s "
                "AND txn_type='WITHDRAWAL' AND DATE(txn_time)=CURDATE()", (s[0],))
    today = cur.fetchone()[0]
    if today + amt > DAILY_LIMIT:
        print("Daily limit of Rs.", DAILY_LIMIT, "exceeded. Withdrawn today: Rs.", today)
        return
    if acc[3] - amt < min_balance(acc[2]):
        print("Insufficient funds. Minimum balance Rs.", min_balance(acc[2]), "must remain.")
        return
    new_bal = round(acc[3] - amt, 2)
    set_balance(s[0], new_bal)
    save_txn(s[0], "WITHDRAWAL", amt, new_bal, "Cash withdrawal")
    mydb.commit()
    print("Withdrawn Rs.", amt, "| New balance: Rs.", new_bal)


def transfer(s):
    dst = read_int("Beneficiary account number: ")
    if dst == s[0] or dst == -1:
        print("Invalid beneficiary.")
        return
    amt = read_amount("Amount: ")
    if amt == 0:
        return
    if not step_up(s[2], amt):
        return
    try:
        msg = move_money(s[0], dst, amt, "Transfer to " + str(dst),
                         "Transfer from " + str(s[0]), "TRANSFER_OUT", "TRANSFER_IN")
        if msg == "OK":
            mydb.commit()
            print("Transferred Rs.", amt, "to account", dst)
        else:
            mydb.rollback()
            print("Transfer failed:", msg)
    except mysql.connector.Error as e:
        mydb.rollback()
        print("Error:", e)


def statement(s):
    n = read_int("How many recent transactions? ")
    if n <= 0:
        n = 10
    cur.execute("SELECT txn_id, txn_time, txn_type, amount, balance_after, description "
                "FROM transactions WHERE account_no=%s ORDER BY txn_id DESC LIMIT %s", (s[0], n))
    rows = cur.fetchall()
    print("\nID    Date                 Type            Amount      Balance     Description")
    print("-" * 85)
    for r in rows:
        print(r[0], "  ", str(r[1])[:16], "  ", r[2].ljust(14), str(r[3]).rjust(10),
              str(r[4]).rjust(12), "  ", r[5])


def change_pin(s):
    acc = get_account(s[0])
    old = input("Current PIN: ").strip()
    if hash_pin(old) != acc[4]:
        print("Wrong PIN.")
        return
    if not otp_challenge("PC" + s[2], "SMS", s[2]):
        print("OTP failed.")
        return
    new = input("New PIN (4-6 digits): ").strip()
    if not valid_pin(new) or new != input("Confirm new PIN: ").strip():
        print("Invalid PIN or not matching.")
        return
    cur.execute("UPDATE accounts SET pin_hash=%s WHERE account_no=%s", (hash_pin(new), s[0]))
    mydb.commit()
    print("PIN changed successfully.")


def calc_emi(p, rate, n):
    r = rate / 1200
    emi = p * r * math.pow(1 + r, n) / (math.pow(1 + r, n) - 1)
    return round(emi, 2)


def apply_loan(s):
    acc = get_account(s[0])
    cur.execute("SELECT COUNT(*) FROM loans WHERE account_no=%s AND status='ACTIVE'", (s[0],))
    if cur.fetchone()[0] >= 2:
        print("Maximum 2 active loans allowed.")
        return
    limit = round(acc[3] * 5, 2)
    print("You can borrow from Rs.", LOAN_MIN, "to Rs.", limit, "at", LOAN_RATE, "% per year")
    if limit < LOAN_MIN:
        print("Balance too low for a loan.")
        return
    amt = read_amount("Loan amount: ")
    if amt < LOAN_MIN or amt > limit:
        print("Amount not in eligible range.")
        return
    months = read_int("Tenure in months (6 to 60): ")
    if months < 6 or months > 60:
        print("Invalid tenure.")
        return
    emi = calc_emi(amt, LOAN_RATE, months)
    total = round(emi * months, 2)
    print("EMI = Rs.", emi, "x", months, "months = Rs.", total, "(interest Rs.", round(total - amt, 2), ")")
    if input("Confirm loan (y/n)? ").lower() != "y":
        return
    if not otp_challenge("LN" + s[2], "SMS", s[2]):
        print("OTP failed.")
        return
    try:
        cur.execute("INSERT INTO loans (account_no, principal, rate, months, emi, outstanding, start_date) "
                    "VALUES (%s,%s,%s,%s,%s,%s,CURDATE())", (s[0], amt, LOAN_RATE, months, emi, total))
        loan_id = cur.lastrowid
        new_bal = round(acc[3] + amt, 2)
        set_balance(s[0], new_bal)
        save_txn(s[0], "LOAN_CREDIT", amt, new_bal, "Loan #" + str(loan_id) + " disbursed")
        mydb.commit()
        print("Loan #" + str(loan_id), "approved. Rs.", amt, "credited. New balance: Rs.", new_bal)
    except mysql.connector.Error as e:
        mydb.rollback()
        print("Error:", e)


def show_loans(s):
    cur.execute("SELECT loan_id, status, principal, emi, emis_paid, months, outstanding "
                "FROM loans WHERE account_no=%s", (s[0],))
    rows = cur.fetchall()
    if len(rows) == 0:
        print("No loans found.")
    for r in rows:
        print("Loan #" + str(r[0]), "|", r[1], "| Principal:", r[2], "| EMI:", r[3],
              "| Paid:", str(r[4]) + "/" + str(r[5]), "| Outstanding:", r[6])


def pay_emi(s, foreclose):
    loan_id = read_int("Loan ID: ")
    cur.execute("SELECT emi, outstanding, emis_paid FROM loans "
                "WHERE loan_id=%s AND account_no=%s AND status='ACTIVE'", (loan_id, s[0]))
    loan = cur.fetchone()
    if loan is None:
        print("Active loan not found.")
        return
    if foreclose:
        amt = loan[1]
        paid = loan[2]
    else:
        amt = min(loan[0], loan[1])
        paid = loan[2] + 1
    acc = get_account(s[0])
    if acc[3] - amt < min_balance(acc[2]):
        print("Insufficient balance to pay Rs.", amt)
        return
    new_bal = round(acc[3] - amt, 2)
    left = round(loan[1] - amt, 2)
    if left <= 0.5:
        status = "CLOSED"
        left = 0
    else:
        status = "ACTIVE"
    set_balance(s[0], new_bal)
    cur.execute("UPDATE loans SET outstanding=%s, emis_paid=%s, status=%s WHERE loan_id=%s",
                (left, paid, status, loan_id))
    save_txn(s[0], "LOAN_EMI", amt, new_bal, "Payment for loan #" + str(loan_id))
    mydb.commit()
    print("Paid Rs.", amt, "| Outstanding: Rs.", left, "| Loan", status)


def fd_rate(months):
    if months <= 6:
        return 5.5
    elif months <= 12:
        return 6.5
    elif months <= 36:
        return 7.0
    return 7.25


def compound(p, rate, years):

    return round(p * math.pow(1 + rate / 400, 4 * years), 2)


def open_fd(s):
    amt = read_amount("FD amount (min Rs." + str(FD_MIN) + "): ")
    if amt < FD_MIN:
        print("Below minimum FD amount.")
        return
    months = read_int("Tenure in months (3 to 120): ")
    if months < 3 or months > 120:
        print("Invalid tenure.")
        return
    rate = fd_rate(months)
    maturity = compound(amt, rate, months / 12)
    print("Interest rate:", rate, "% | Maturity amount: Rs.", maturity)
    if input("Confirm (y/n)? ").lower() != "y":
        return
    if not step_up(s[2], amt):
        return
    acc = get_account(s[0])
    if acc[3] - amt < min_balance(acc[2]):
        print("Insufficient funds.")
        return
    try:
        new_bal = round(acc[3] - amt, 2)
        set_balance(s[0], new_bal)
        cur.execute("INSERT INTO fixed_deposits (account_no, principal, rate, months, start_date, "
                    "maturity_date, maturity_amount) VALUES (%s,%s,%s,%s,CURDATE(),"
                    "DATE_ADD(CURDATE(), INTERVAL %s MONTH),%s)",
                    (s[0], amt, rate, months, months, maturity))
        fd_id = cur.lastrowid
        save_txn(s[0], "FD_OPEN", amt, new_bal, "FD #" + str(fd_id) + " opened")
        mydb.commit()
        print("FD #" + str(fd_id), "created successfully.")
    except mysql.connector.Error as e:
        mydb.rollback()
        print("Error:", e)


def show_fds(s):
    cur.execute("SELECT fd_id, status, principal, rate, months, maturity_date, maturity_amount "
                "FROM fixed_deposits WHERE account_no=%s", (s[0],))
    rows = cur.fetchall()
    if len(rows) == 0:
        print("No fixed deposits.")
    for r in rows:
        print("FD #" + str(r[0]), "|", r[1], "| Rs.", r[2], "@", r[3], "% |", r[4],
              "months | Matures on", r[5], "-> Rs.", r[6])


def close_fd(s):
    fd_id = read_int("FD ID: ")
    cur.execute("SELECT principal, rate, maturity_amount, DATEDIFF(CURDATE(), start_date), "
                "DATEDIFF(CURDATE(), maturity_date) FROM fixed_deposits "
                "WHERE fd_id=%s AND account_no=%s AND status='ACTIVE'", (fd_id, s[0]))
    fd = cur.fetchone()
    if fd is None:
        print("Active FD not found.")
        return
    if fd[4] >= 0:
        payout = fd[2]
        status = "MATURED"
        note = "FD matured"
    else:
        rate = max(fd[1] - FD_PENALTY, 0)
        payout = compound(fd[0], rate, fd[3] / 365)
        status = "BROKEN"
        note = "FD closed early"
        print("FD has not matured. Early payout (with penalty) = Rs.", payout)
        if input("Proceed (y/n)? ").lower() != "y":
            return
    acc = get_account(s[0])
    new_bal = round(acc[3] + payout, 2)
    set_balance(s[0], new_bal)
    cur.execute("UPDATE fixed_deposits SET status=%s WHERE fd_id=%s", (status, fd_id))
    save_txn(s[0], "FD_PAYOUT", payout, new_bal, note + " #" + str(fd_id))
    mydb.commit()
    print("Rs.", payout, "credited. New balance: Rs.", new_bal)


def issue_cheque_book(s):
    n = read_int("Number of leaves (10 / 25 / 50): ")
    if n != 10 and n != 25 and n != 50:
        print("Choose 10, 25 or 50.")
        return
    first = 0
    last = 0
    for i in range(n):
        cur.execute("INSERT INTO cheques (account_no, issue_date) VALUES (%s, CURDATE())", (s[0],))
        if i == 0:
            first = cur.lastrowid
        last = cur.lastrowid
    mydb.commit()
    print("Cheque book issued. Cheque numbers", first, "to", last)


def write_cheque(s):
    cno = read_int("Cheque number: ")
    payee = read_int("Payee account number: ")
    amt = read_amount("Amount: ")
    if amt == 0 or payee == -1:
        return
    cur.execute("UPDATE cheques SET payee_account=%s, amount=%s, written_date=CURDATE(), "
                "status='PRESENTED' WHERE cheque_no=%s AND account_no=%s AND status='UNUSED'",
                (payee, amt, cno, s[0]))
    if cur.rowcount == 0:
        print("Cheque not found or already used.")
    else:
        print("Cheque", cno, "written for Rs.", amt, "to account", payee)
    mydb.commit()


def clear_cheque(s):

    cno = read_int("Cheque number to deposit: ")
    cur.execute("SELECT account_no, amount, DATEDIFF(CURDATE(), written_date) FROM cheques "
                "WHERE cheque_no=%s AND payee_account=%s AND status='PRESENTED'", (cno, s[0]))
    c = cur.fetchone()
    if c is None:
        print("Cheque not found or not payable to your account.")
        return
    if c[2] > 90:
        cur.execute("UPDATE cheques SET status='BOUNCED' WHERE cheque_no=%s", (cno,))
        mydb.commit()
        print("Cheque is older than 90 days. BOUNCED.")
        return
    try:
        msg = move_money(c[0], s[0], c[1], "Cheque " + str(cno) + " paid",
                         "Cheque " + str(cno) + " credited", "CHEQUE_DEBIT", "CHEQUE_CREDIT")
        if msg == "OK":
            cur.execute("UPDATE cheques SET status='CLEARED' WHERE cheque_no=%s", (cno,))
            mydb.commit()
            print("Cheque cleared. Rs.", c[1], "credited to your account.")
        else:
            mydb.rollback()
            cur.execute("UPDATE cheques SET status='BOUNCED' WHERE cheque_no=%s", (cno,))
            mydb.commit()
            print("Cheque BOUNCED:", msg)
    except mysql.connector.Error as e:
        mydb.rollback()
        print("Error:", e)


def show_cheques(s):
    cur.execute("SELECT cheque_no, account_no, payee_account, amount, status FROM cheques "
                "WHERE account_no=%s OR payee_account=%s ORDER BY cheque_no", (s[0], s[0]))
    for r in cur.fetchall():
        if r[1] == s[0]:
            role = "DRAWER"
        else:
            role = "PAYEE"
        print("Cheque", r[0], "|", role, "|", r[4], "| Payee:", r[2], "| Amount:", r[3])


def cancel_cheque(s):
    cno = read_int("Cheque number to cancel: ")
    cur.execute("UPDATE cheques SET status='CANCELLED' WHERE cheque_no=%s AND account_no=%s "
                "AND status IN ('UNUSED','PRESENTED')", (cno, s[0]))
    if cur.rowcount == 0:
        print("Cannot cancel this cheque.")
    else:
        print("Cheque cancelled.")
    mydb.commit()


def loan_menu(s):
    print("\n--- LOANS ---")
    print("1. Apply for loan\n2. My loans\n3. Pay EMI\n4. Foreclose loan\n0. Back")
    c = input("Choice: ").strip()
    if c == "1":
        apply_loan(s)
    elif c == "2":
        show_loans(s)
    elif c == "3":
        pay_emi(s, False)
    elif c == "4":
        pay_emi(s, True)


def fd_menu(s):
    print("\n--- FIXED DEPOSITS ---")
    print("1. Open FD\n2. My FDs\n3. Close / claim FD\n0. Back")
    c = input("Choice: ").strip()
    if c == "1":
        open_fd(s)
    elif c == "2":
        show_fds(s)
    elif c == "3":
        close_fd(s)


def cheque_menu(s):
    print("\n--- CHEQUES ---")
    print("1. Request cheque book\n2. Write a cheque\n3. Deposit a received cheque")
    print("4. My cheques\n5. Cancel a cheque\n0. Back")
    c = input("Choice: ").strip()
    if c == "1":
        issue_cheque_book(s)
    elif c == "2":
        write_cheque(s)
    elif c == "3":
        clear_cheque(s)
    elif c == "4":
        show_cheques(s)
    elif c == "5":
        cancel_cheque(s)


def account_menu(s):
    while True:
        print("\n===== ACCOUNT", s[0], "-", s[1], "=====")
        print("1. Check balance")
        print("2. Deposit")
        print("3. Withdraw")
        print("4. Transfer money")
        print("5. Mini statement")
        print("6. Loans")
        print("7. Fixed deposits")
        print("8. Cheques")
        print("9. Change PIN")
        print("0. Logout")
        c = input("Choice: ").strip()
        if c == "1":
            show_balance(s)
        elif c == "2":
            deposit(s)
        elif c == "3":
            withdraw(s)
        elif c == "4":
            transfer(s)
        elif c == "5":
            statement(s)
        elif c == "6":
            loan_menu(s)
        elif c == "7":
            fd_menu(s)
        elif c == "8":
            cheque_menu(s)
        elif c == "9":
            change_pin(s)
        elif c == "0":
            print("Logged out.")
            pause()
            return
        else:
            print("Invalid choice.")


def main():
    try:
        connect_db()
    except mysql.connector.Error as e:
        print("Cannot connect to MySQL:", e)
        print("Check HOST, USER and PASSWORD at the top of the program.")
        sys.exit()

    while True:
        print("\n========== PYTHON BANK ==========")
        print("1. Open new account (dual verification)")
        print("2. Login (PIN + OTP)")
        print("0. Exit")
        c = input("Choice: ").strip()
        if c == "1":
            create_account()
        elif c == "2":
            session = login()
            if session is not None:
                account_menu(session)
        elif c == "0":
            print("Thank you for banking with us!")
            mydb.close()
            sys.exit()
        else:
            print("Invalid choice.")


main()