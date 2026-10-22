import random
import datetime
import time
import sys

def generate_data(env):
    random.seed(42)
    t0 = time.time()
    print("=== STARTING GENERATION OF 30,000 MOVES & 3,000 STATEMENT LINES ===")
    
    comp_a = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1) or env.ref('base.main_company')
    comp_b = env['res.company'].search([('name', '=', 'Europe Corp B')], limit=1)
    
    xaf = env['res.currency'].search([('name', '=', 'XAF')], limit=1)
    eur = env['res.currency'].search([('name', '=', 'EUR')], limit=1)
    usd = env['res.currency'].search([('name', '=', 'USD')], limit=1)
    
    print(f"Company A: {comp_a.name} ({comp_a.currency_id.name})")
    print(f"Company B: {comp_b.name} ({comp_b.currency_id.name})")

    # 1. 200 Partenaires
    print("Creating/verifying 200 partners...")
    existing_partners = env['res.partner'].search([('ref', 'like', 'QA_PART_')])
    needed = 200 - len(existing_partners)
    if needed > 0:
        partner_vals = []
        for i in range(len(existing_partners) + 1, len(existing_partners) + needed + 1):
            is_customer = (i % 2 == 1)
            partner_vals.append({
                'name': f"Partenaire CEMAC QA {i:03d} {'Client' if is_customer else 'Fournisseur'}",
                'ref': f"QA_PART_{i:03d}",
                'customer_rank': 1 if is_customer else 0,
                'supplier_rank': 0 if is_customer else 1,
                'email': f"partenaire_{i:03d}@example-cemac.org",
            })
        env['res.partner'].create(partner_vals)
    partners = env['res.partner'].search([('ref', 'like', 'QA_PART_')], limit=200)
    print(f"Total QA Partners ready: {len(partners)}")

    # Get accounts and journals
    def get_comp_data(comp):
        journals = env['account.journal'].search([('company_id', '=', comp.id)])
        j_sale = journals.filtered(lambda j: j.type == 'sale')[:1]
        j_purch = journals.filtered(lambda j: j.type == 'purchase')[:1]
        j_bank = journals.filtered(lambda j: j.type == 'bank')[:1]
        j_misc = journals.filtered(lambda j: j.type == 'general')[:1]
        
        accounts = env['account.account'].search([('company_ids', 'in', comp.id)])
        rec_acc = accounts.filtered(lambda a: a.account_type == 'asset_receivable')[:1]
        pay_acc = accounts.filtered(lambda a: a.account_type == 'liability_payable')[:1]
        rev_acc = accounts.filtered(lambda a: a.account_type == 'income')[:1]
        exp_acc = accounts.filtered(lambda a: a.account_type == 'expense')[:1]
        bank_acc = j_bank.default_account_id or accounts.filtered(lambda a: a.account_type == 'asset_cash')[:1]

        
        return {
            'comp': comp,
            'j_sale': j_sale, 'j_purch': j_purch, 'j_bank': j_bank, 'j_misc': j_misc,
            'rec': rec_acc, 'pay': pay_acc, 'rev': rev_acc, 'exp': exp_acc, 'bank_acc': bank_acc
        }

    data_a = get_comp_data(comp_a)
    data_b = get_comp_data(comp_b)

    # 2. Generate 30,000 moves via high-speed SQL insertion
    print("\nGenerating 30,000 moves (2024-2025)...")
    env.cr.execute("SELECT count(*) FROM account_move")
    existing_moves = env.cr.fetchone()[0]
    
    TOTAL_TARGET_MOVES = 30000
    if existing_moves < TOTAL_TARGET_MOVES:
        moves_to_create = TOTAL_TARGET_MOVES - existing_moves
        print(f"Inserting {moves_to_create} moves...")
        
        # We will insert in chunks of 5000 moves
        chunk_size = 5000
        start_date_2024 = datetime.date(2024, 1, 1)
        end_date_2025 = datetime.date(2025, 12, 31)
        total_days = (end_date_2025 - start_date_2024).days
        
        partner_ids = partners.ids
        
        created_count = 0
        while created_count < moves_to_create:
            current_batch_size = min(chunk_size, moves_to_create - created_count)
            move_records = []
            line_records = []
            
            # Fetch next IDs from sequence
            env.cr.execute(f"SELECT nextval('account_move_id_seq') FROM generate_series(1, {current_batch_size})")
            move_ids = [r[0] for r in env.cr.fetchall()]
            
            # 2 lines per move -> current_batch_size * 2 lines
            env.cr.execute(f"SELECT nextval('account_move_line_id_seq') FROM generate_series(1, {current_batch_size * 2})")
            line_ids = [r[0] for r in env.cr.fetchall()]
            
            for idx in range(current_batch_size):
                m_id = move_ids[idx]
                line_id1 = line_ids[idx * 2]
                line_id2 = line_ids[idx * 2 + 1]
                
                # 80% Company A, 20% Company B
                is_comp_a = (random.random() < 0.8)
                d = data_a if is_comp_a else data_b
                comp_id = d['comp'].id
                base_curr = d['comp'].currency_id
                
                # Dates distributed over 2024 and 2025
                move_date = start_date_2024 + datetime.timedelta(days=random.randint(0, total_days))
                
                partner_id = random.choice(partner_ids)
                
                # Move type: 45% out_invoice, 35% in_invoice, 10% entry/payment, 10% refund
                dice = random.random()
                if dice < 0.45:
                    m_type = 'out_invoice'
                    j = d['j_sale']
                    acc_debit = d['rec'].id
                    acc_credit = d['rev'].id
                    m_name = f"FAC/{move_date.year}/{m_id:06d}"
                elif dice < 0.80:
                    m_type = 'in_invoice'
                    j = d['j_purch']
                    acc_debit = d['exp'].id
                    acc_credit = d['pay'].id
                    m_name = f"ACH/{move_date.year}/{m_id:06d}"
                elif dice < 0.90:
                    m_type = 'out_refund'
                    j = d['j_sale']
                    acc_debit = d['rev'].id
                    acc_credit = d['rec'].id
                    m_name = f"AV/{move_date.year}/{m_id:06d}"
                else:
                    m_type = 'entry'
                    j = d['j_misc']
                    acc_debit = d['bank_acc'].id if d['bank_acc'] else d['exp'].id
                    acc_credit = d['rec'].id
                    m_name = f"OD/{move_date.year}/{m_id:06d}"
                
                # 5% foreign currency
                is_foreign = (random.random() < 0.05)
                if is_foreign:
                    foreign_curr = usd if random.random() < 0.5 else (eur if is_comp_a else xaf)
                    curr_id = foreign_curr.id
                    # amount in foreign currency
                    amt_foreign = round(random.uniform(50.0, 5000.0), 2)
                    rate = 655.957 if (is_comp_a and foreign_curr == eur) else (600.0 if is_comp_a else 0.0015)
                    amt_base = round(amt_foreign * rate, 0 if is_comp_a else 2)
                else:
                    curr_id = base_curr.id
                    amt_base = round(random.uniform(1000.0, 500000.0), 0 if is_comp_a else 2)
                    amt_foreign = amt_base

                move_records.append((
                    m_id, m_name, j.id, comp_id, curr_id, 'posted', m_type, 'no',
                    move_date, partner_id, partner_id, amt_base, 0.0,
                    datetime.datetime.now(), datetime.datetime.now(), 1, 1
                ))
                
                # Line 1 (Debit)
                line_records.append((
                    line_id1, m_id, comp_id, curr_id, partner_id, acc_debit, j.id,
                    'posted', move_date, f"{m_name} L1", amt_base, 0.0, amt_base,
                    amt_foreign if curr_id != base_curr.id else amt_base,
                    'product' if m_type in ('out_invoice', 'in_invoice') else 'payment_term',
                    amt_base, 1, 1, datetime.datetime.now(), datetime.datetime.now()
                ))
                
                # Line 2 (Credit)
                line_records.append((
                    line_id2, m_id, comp_id, curr_id, partner_id, acc_credit, j.id,
                    'posted', move_date, f"{m_name} L2", 0.0, amt_base, -amt_base,
                    -amt_foreign if curr_id != base_curr.id else -amt_base,
                    'payment_term' if m_type in ('out_invoice', 'in_invoice') else 'product',
                    amt_base, 1, 1, datetime.datetime.now(), datetime.datetime.now()
                ))

            # Batch insert account_move
            args_move = b",".join(env.cr.mogrify(
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", r
            ) for r in move_records)
            env.cr.execute(b"""
                INSERT INTO account_move (
                    id, name, journal_id, company_id, currency_id, state, move_type, auto_post,
                    date, partner_id, commercial_partner_id, amount_total, amount_residual,
                    create_date, write_date, create_uid, write_uid
                ) VALUES """ + args_move)

            # Batch insert account_move_line
            args_line = b",".join(env.cr.mogrify(
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", r
            ) for r in line_records)
            env.cr.execute(b"""
                INSERT INTO account_move_line (
                    id, move_id, company_id, currency_id, partner_id, account_id, journal_id,
                    parent_state, date, name, debit, credit, balance, amount_currency,
                    display_type, amount_residual, create_uid, write_uid, create_date, write_date
                ) VALUES """ + args_line)

            created_count += current_batch_size
            print(f"  Inserted batch: {created_count}/{moves_to_create} moves...")
            env.cr.commit()

    env.cr.execute("SELECT count(*) FROM account_move")
    total_moves_final = env.cr.fetchone()[0]
    env.cr.execute("SELECT count(*) FROM account_move_line")
    total_lines_final = env.cr.fetchone()[0]
    print(f"TOTAL MOVES IN DB: {total_moves_final} | TOTAL LINES: {total_lines_final}")

    # 3. Generate 3,000 Bank Statement Lines (om_account_reconcile)
    print("\nGenerating 3,000 bank statement lines on Bank Journal (Company A)...")
    j_bank_a = data_a['j_bank']

    
    # Create or get Bank Statement
    st = env['account.bank.statement'].search([('journal_id', '=', j_bank_a.id)], limit=1)
    if not st:
        st = env['account.bank.statement'].create({
            'name': 'Releve Annuel 2025 CEMAC',
            'journal_id': j_bank_a.id,
            'date': '2025-12-31',
        })
    
    env.cr.execute("SELECT count(*) FROM account_bank_statement_line WHERE statement_id = %s", [st.id])
    existing_st_lines = env.cr.fetchone()[0]
    
    TARGET_ST_LINES = 3000
    if existing_st_lines < TARGET_ST_LINES:
        st_lines_needed = TARGET_ST_LINES - existing_st_lines
        print(f"Creating {st_lines_needed} statement lines...")
        
        st_records = []
        st_move_records = []
        st_line_records = []
        
        env.cr.execute(f"SELECT nextval('account_bank_statement_line_id_seq') FROM generate_series(1, {st_lines_needed})")
        st_line_ids = [r[0] for r in env.cr.fetchall()]
        
        env.cr.execute(f"SELECT nextval('account_move_id_seq') FROM generate_series(1, {st_lines_needed})")
        st_move_ids = [r[0] for r in env.cr.fetchall()]
        
        env.cr.execute(f"SELECT nextval('account_move_line_id_seq') FROM generate_series(1, {st_lines_needed * 2})")
        st_aml_ids = [r[0] for r in env.cr.fetchall()]
        
        start_date = datetime.date(2025, 1, 1)
        bank_acc_id = data_a['bank_acc'].id
        suspense_acc_id = j_bank_a.suspense_account_id.id or data_a['exp'].id
        
        partner_ids = partners.ids
        
        for idx in range(st_lines_needed):
            s_id = st_line_ids[idx]
            m_id = st_move_ids[idx]
            l1_id = st_aml_ids[idx * 2]
            l2_id = st_aml_ids[idx * 2 + 1]
            
            p_id = random.choice(partner_ids)
            s_date = start_date + datetime.timedelta(days=random.randint(0, 360))
            
            # Patterns
            if idx < 50:
                amount = 50000.0
                ref = f"VIREMENT EXACT 50K REF_{idx:03d}"
            elif idx < 100:
                amount = 25000.0
                ref = f"ACOMPTE PARTIEL REF_{idx:03d}"
            elif idx == 101:
                amount = 300000.0
                ref = "REGLEMENT GROUPE 3 FACTURES"
            elif 102 <= idx <= 104:
                amount = 40000.0
                ref = f"REGLEMENT FRACTIONNE #{idx-101}"
            elif idx < 120:
                amount = 65596.0
                ref = f"VIREMENT INTERNATIONAL EUR REF_{idx:03d}"
            else:
                amount = round(random.uniform(5000.0, 750000.0), 0)
                if random.random() < 0.3:
                    amount = -amount
                ref = f"REGLEMENT OP_{idx:04d}"

            # Bank statement line
            st_records.append((
                s_id, m_id, j_bank_a.id, comp_a.id, st.id, p_id, xaf.id,
                ref, amount, False, amount, 1, 1, datetime.datetime.now(), datetime.datetime.now()
            ))
            
            # Account Move for statement line
            m_name = f"BNK1/{s_date.year}/{s_id:05d}"
            st_move_records.append((
                m_id, m_name, j_bank_a.id, comp_a.id, xaf.id, 'posted', 'entry', 'no',
                s_date, p_id, p_id, abs(amount), 0.0,
                datetime.datetime.now(), datetime.datetime.now(), 1, 1
            ))
            
            debit = amount if amount > 0 else 0.0
            credit = -amount if amount < 0 else 0.0
            balance = amount
            
            st_line_records.append((
                l1_id, m_id, comp_a.id, xaf.id, p_id, bank_acc_id, j_bank_a.id,
                'posted', s_date, ref, debit, credit, balance, balance,
                'product', 0.0, 1, 1, datetime.datetime.now(), datetime.datetime.now()
            ))
            st_line_records.append((
                l2_id, m_id, comp_a.id, xaf.id, p_id, suspense_acc_id, j_bank_a.id,
                'posted', s_date, ref, credit, debit, -balance, -balance,
                'product', 0.0, 1, 1, datetime.datetime.now(), datetime.datetime.now()
            ))

        # Insert statements moves
        args_sm = b",".join(env.cr.mogrify(
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", r
        ) for r in st_move_records)
        env.cr.execute(b"""
            INSERT INTO account_move (
                id, name, journal_id, company_id, currency_id, state, move_type, auto_post,
                date, partner_id, commercial_partner_id, amount_total, amount_residual,
                create_date, write_date, create_uid, write_uid
            ) VALUES """ + args_sm)

        # Insert statements move lines
        args_sml = b",".join(env.cr.mogrify(
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", r
        ) for r in st_line_records)
        env.cr.execute(b"""
            INSERT INTO account_move_line (
                id, move_id, company_id, currency_id, partner_id, account_id, journal_id,
                parent_state, date, name, debit, credit, balance, amount_currency,
                display_type, amount_residual, create_uid, write_uid, create_date, write_date
            ) VALUES """ + args_sml)

        # Insert statement lines
        args_st = b",".join(env.cr.mogrify(
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", r
        ) for r in st_records)
        env.cr.execute(b"""
            INSERT INTO account_bank_statement_line (
                id, move_id, journal_id, company_id, statement_id, partner_id, currency_id,
                payment_ref, amount, is_reconciled, amount_residual, create_uid, write_uid, create_date, write_date
            ) VALUES """ + args_st)
            
        env.cr.commit()
        print(f"Inserted {st_lines_needed} bank statement lines successfully.")


    env.cr.execute("SELECT count(*) FROM account_bank_statement_line")
    total_st_final = env.cr.fetchone()[0]
    print(f"TOTAL STATEMENT LINES IN DB: {total_st_final}")
    print(f"Dataset generated in {round(time.time() - t0, 2)}s.")
    print("=== DATASET GENERATION COMPLETE ===")

if __name__ == "__main__":
    # If run in Odoo shell
    if 'env' in locals() or 'env' in globals():
        generate_data(env)
    else:
        print("Run this script via: docker exec -i odoo19_accounting_web odoo shell -d odoo19_cemac --no-http -p 8079 < audit_tooling/generate_dataset.py")
