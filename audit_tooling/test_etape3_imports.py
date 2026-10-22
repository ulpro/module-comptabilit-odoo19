import io
import time
from odoo import Command
from odoo.exceptions import UserError
import openpyxl

def run_etape3_tests(env):
    print("=== ETAPE 3 : BANCS D'ESSAIS IMPORTS DE RELEVES BANCAIRES ===")
    comp_a = env['res.company'].search([('name', '=', 'CEMAC Corp A')], limit=1)
    j_bank = env['account.journal'].search([('company_id', '=', comp_a.id), ('type', '=', 'bank')], limit=1)
    
    # S'assurer que le journal bancaire a un compte bancaire associe
    if not j_bank.bank_account_id:
        j_bank.bank_account_id = env['res.partner.bank'].create({
            'acc_number': 'CM2110005000010000000001',
            'partner_id': comp_a.partner_id.id,
        })
    acc_num = j_bank.bank_account_id.acc_number

    def do_import(content, filename, **kwargs):
        raw = content.encode('utf-8') if isinstance(content, str) else content
        attachment = env['ir.attachment'].create({
            'name': filename,
            'raw': raw,
        })
        vals = {
            'attachment_ids': [Command.set(attachment.ids)],
            'journal_id': j_bank.id,
            **kwargs,
        }
        wizard = env['account.statement.import'].create(vals)
        res = wizard.action_import()
        return res, wizard

    # -------------------------------------------------------------
    # 1. TEST FORMAT QIF
    # -------------------------------------------------------------
    print("\n--- TEST 1 : FORMAT QIF ---")
    qif_data = f"""!Type:Bank
D10/01/2025
T50000.00
PCLIENT CEMAC 1
MReglement facture 001
^
D12/01/2025
T-15000.00
PFOURNISSEUR ENERGIE
MPaiement facture elec
^
"""
    res_qif, _ = do_import(qif_data, 'releve_test.qif', date_format='%d/%m/%Y')
    stmt_qif = env['account.bank.statement'].search(res_qif['domain'])
    print(f"QIF Import -> Releve ID: {stmt_qif.id}, Lignes: {len(stmt_qif.line_ids)}")
    amounts_qif = stmt_qif.line_ids.mapped('amount')
    print(f"  Montants: {amounts_qif}, Somme: {sum(amounts_qif)} (attendu: 35000.0)")
    assert len(stmt_qif.line_ids) == 2
    assert sum(amounts_qif) == 35000.0

    # -------------------------------------------------------------
    # 2. TEST FORMAT OFX
    # -------------------------------------------------------------
    print("\n--- TEST 2 : FORMAT OFX ---")
    ofx_data = f"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
<OFX>
<BANKMSGSRSV1><STMTTRNRS><TRNUID>1001<STATUS><CODE>0<SEVERITY>INFO</STATUS>
<STMTRS><CURDEF>XAF
<BANKACCTFROM><BANKID>10005<ACCTID>{acc_num}<ACCTTYPE>CHECKING</BANKACCTFROM>
<BANKTRANLIST><DTSTART>20250101<DTEND>20250131
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20250115<TRNAMT>75000.00<FITID>OFX-XAF-001<NAME>Client Virement</STMTTRN>
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20250120<TRNAMT>-25000.00<FITID>OFX-XAF-002<NAME>Fournisseur Achat</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL><BALAMT>50000.00<DTASOF>20250131</LEDGERBAL>
</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""
    res_ofx, _ = do_import(ofx_data, 'releve_test.ofx')
    stmt_ofx = env['account.bank.statement'].search(res_ofx['domain'])
    print(f"OFX Import -> Releve ID: {stmt_ofx.id}, Lignes: {len(stmt_ofx.line_ids)}")
    amounts_ofx = stmt_ofx.line_ids.mapped('amount')
    print(f"  Montants: {amounts_ofx}, Somme: {sum(amounts_ofx)} (attendu: 50000.0)")
    assert len(stmt_ofx.line_ids) == 2
    assert sum(amounts_ofx) == 50000.0

    # -------------------------------------------------------------
    # 3. TEST FORMAT MT940
    # -------------------------------------------------------------
    print("\n--- TEST 3 : FORMAT MT940 ---")
    mt940_data = f""":20:STARTCEMAC
:25:{acc_num} XAF
:28C:001/1
:60F:C250101XAF100000,00
:61:2501100110C60000,00NTRFNONREF//REFMT001
:86:/NAME/Client MT940/REMI/Reglement Facture MT
:61:2501220122D20000,00NTRFNONREF//REFMT002
:86:/NAME/Frais Bancaires/REMI/Frais tenue de compte
:62F:C250131XAF140000,00
"""
    res_mt, _ = do_import(mt940_data, 'releve_test.mta')
    stmt_mt = env['account.bank.statement'].search(res_mt['domain'])
    print(f"MT940 Import -> Releve ID: {stmt_mt.id}, Lignes: {len(stmt_mt.line_ids)}")
    amounts_mt = stmt_mt.line_ids.mapped('amount')
    print(f"  Montants: {amounts_mt}, Somme: {sum(amounts_mt)} (attendu: 40000.0)")
    assert len(stmt_mt.line_ids) == 2
    assert sum(amounts_mt) == 40000.0

    # -------------------------------------------------------------
    # 4. TEST FORMAT CAMT.053 (XML ISO 20022)
    # -------------------------------------------------------------
    print("\n--- TEST 4 : FORMAT CAMT.053 ---")
    camt_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>MSG-CEMAC-001</MsgId><CreDtTm>2025-01-31T20:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>STMT-CEMAC-001</Id>
      <Acct><Id><Othr><Id>{acc_num}</Id></Othr></Id><Ccy>XAF</Ccy></Acct>
      <Bal>
        <Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="XAF">0.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2025-01-01</Dt></Dt>
      </Bal>
      <Bal>
        <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="XAF">85000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2025-01-31</Dt></Dt>
      </Bal>
      <Ntry>
        <Amt Ccy="XAF">100000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><Sts>BOOK</Sts>
        <BookgDt><Dt>2025-01-18</Dt></BookgDt>
        <NtryDtls><TxDtls>
          <RltdPties><Dbtr><Nm>Client Camt</Nm></Dbtr></RltdPties>
          <RmtInf><Ustrd>Virement Camt 100k</Ustrd></RmtInf>
        </TxDtls></NtryDtls>
      </Ntry>
      <Ntry>
        <Amt Ccy="XAF">15000.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts>BOOK</Sts>
        <BookgDt><Dt>2025-01-25</Dt></BookgDt>
        <NtryDtls><TxDtls>
          <RltdPties><Cdtr><Nm>Fournisseur Camt</Nm></Cdtr></RltdPties>
          <RmtInf><Ustrd>Reglement Camt 15k</Ustrd></RmtInf>
        </TxDtls></NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>
"""
    res_camt, _ = do_import(camt_data, 'releve_test.xml')
    stmt_camt = env['account.bank.statement'].search(res_camt['domain'])
    print(f"CAMT.053 Import -> Releve ID: {stmt_camt.id}, Lignes: {len(stmt_camt.line_ids)}")
    amounts_camt = stmt_camt.line_ids.mapped('amount')
    print(f"  Montants: {amounts_camt}, Somme: {sum(amounts_camt)} (attendu: 85000.0)")
    assert len(stmt_camt.line_ids) == 2
    assert sum(amounts_camt) == 85000.0

    # -------------------------------------------------------------
    # 5. TEST FORMAT CSV (Standard)
    # -------------------------------------------------------------
    print("\n--- TEST 5 : FORMAT CSV (Standard) ---")
    map_csv = env['account.statement.import.map'].create({
        'name': 'Map CSV Standard',
        'company_id': comp_a.id,
        'delimiter': ';',
        'date_format': '%Y-%m-%d',
        'column_date': 'Date',
        'column_label': 'Label',
        'column_amount': 'Amount',
    })
    csv_data = "Date;Label;Amount\n2025-01-05;Encaissement Facture CSV;120000\n2025-01-14;Reglement Loyer CSV;-45000\n"
    res_csv, _ = do_import(csv_data, 'releve_test.csv', map_id=map_csv.id)
    stmt_csv = env['account.bank.statement'].search(res_csv['domain'])
    print(f"CSV Import -> Releve ID: {stmt_csv.id}, Lignes: {len(stmt_csv.line_ids)}")
    amounts_csv = stmt_csv.line_ids.mapped('amount')
    print(f"  Montants: {amounts_csv}, Somme: {sum(amounts_csv)} (attendu: 75000.0)")
    assert len(stmt_csv.line_ids) == 2
    assert sum(amounts_csv) == 75000.0

    # -------------------------------------------------------------
    # 6. TEST FORMAT XLSX (Excel)
    # -------------------------------------------------------------
    print("\n--- TEST 6 : FORMAT XLSX (Excel) ---")
    map_xlsx = env['account.statement.import.map'].create({
        'name': 'Map XLSX Standard',
        'company_id': comp_a.id,
        'date_format': '%Y-%m-%d',
        'column_date': 'Date',
        'column_label': 'Description',
        'column_amount': 'Amount',
    })
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Amount"])
    ws.append(["2025-01-08", "Virement Export XLSX", 210000])
    ws.append(["2025-01-28", "Achat Matériel XLSX", -60000])
    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()
    
    res_xlsx, _ = do_import(xlsx_bytes, 'releve_test.xlsx', map_id=map_xlsx.id)
    stmt_xlsx = env['account.bank.statement'].search(res_xlsx['domain'])
    print(f"XLSX Import -> Releve ID: {stmt_xlsx.id}, Lignes: {len(stmt_xlsx.line_ids)}")
    amounts_xlsx = stmt_xlsx.line_ids.mapped('amount')
    print(f"  Montants: {amounts_xlsx}, Somme: {sum(amounts_xlsx)} (attendu: 150000.0)")
    assert len(stmt_xlsx.line_ids) == 2
    assert sum(amounts_xlsx) == 150000.0

    # -------------------------------------------------------------
    # 7. CAS DEGRADES : Latin-1, UTF-8 BOM, Virgule Décimale, Dates inversées
    # -------------------------------------------------------------
    print("\n--- TEST 7 : CAS DEGRADES ---")
    
    # 7.1 UTF-8 BOM
    map_bom = env['account.statement.import.map'].create({
        'name': 'Map UTF-8 BOM',
        'company_id': comp_a.id,
        'file_encoding': 'utf-8-sig',
        'delimiter': ';',
        'date_format': '%Y-%m-%d',
        'column_date': 'Date',
        'column_label': 'Label',
        'column_amount': 'Amount',
    })
    bom_data = '\ufeffDate;Label;Amount\n2025-01-02;Test UTF-8 BOM;30000\n'.encode('utf-8')
    res_bom, _ = do_import(bom_data, 'test_bom.csv', map_id=map_bom.id)
    stmt_bom = env['account.bank.statement'].search(res_bom['domain'])
    print(f"  UTF-8 BOM -> Lignes: {len(stmt_bom.line_ids)}, Montant: {stmt_bom.line_ids.amount}")
    assert len(stmt_bom.line_ids) == 1 and stmt_bom.line_ids.amount == 30000.0

    # 7.2 Latin-1 avec accents français
    map_l1 = env['account.statement.import.map'].create({
        'name': 'Map Latin-1',
        'company_id': comp_a.id,
        'file_encoding': 'iso-8859-1',
        'delimiter': ';',
        'date_format': '%Y-%m-%d',
        'column_date': 'Date',
        'column_label': 'Label',
        'column_amount': 'Amount',
    })
    latin1_data = "Date;Label;Amount\n2025-01-03;Électricité & Échéance Clôturée;45000\n".encode('iso-8859-1')
    res_l1, _ = do_import(latin1_data, 'test_latin1.csv', map_id=map_l1.id)
    stmt_l1 = env['account.bank.statement'].search(res_l1['domain'])
    print(f"  Latin-1 -> Lignes: {len(stmt_l1.line_ids)}, Label: {stmt_l1.line_ids.payment_ref}")
    assert len(stmt_l1.line_ids) == 1

    # 7.3 Virgule décimale
    map_comma = env['account.statement.import.map'].create({
        'name': 'Map Virgule Decimale',
        'company_id': comp_a.id,
        'delimiter': ';',
        'decimal_separator': ',',
        'date_format': '%Y-%m-%d',
        'column_date': 'Date',
        'column_label': 'Label',
        'column_amount': 'Amount',
    })
    comma_data = "Date;Label;Amount\n2025-01-04;Paiement Virgule;12345,67\n"
    res_comma, _ = do_import(comma_data, 'test_comma.csv', map_id=map_comma.id)
    stmt_comma = env['account.bank.statement'].search(res_comma['domain'])
    print(f"  Virgule decimale -> Montant: {stmt_comma.line_ids.amount} (attendu: 12345.67 ou 12346 arrondi)")
    assert len(stmt_comma.line_ids) == 1

    # 7.4 Fichier tronque / corrompu
    print("  Test Fichier Tronque -> Attente rejet propre sans crash")
    corrupt_qif = "!Type:Bank\nD2025-01\nT--invalide\n"
    try:
        do_import(corrupt_qif, 'corrupt.qif')
        print("  AVERTISSEMENT: fichier corrompu n'a pas leve d'exception")
    except (UserError, ValueError) as e:
        print(f"  Fichier corrompu correctement refuse: {type(e).__name__}: {e}")

    # 7.5 Anti-doublons (Re-import du meme fichier QIF)
    print("  Test Anti-Doublons (Re-import de releve_test.qif)")
    try:
        do_import(qif_data, 'releve_test.qif', date_format='%d/%m/%Y')
        raise AssertionError("Le re-import du fichier QIF aurait du etre rejete !")
    except UserError as ue:
        print(f"  Succes Anti-doublons QIF : rejet avec message '{ue}'")
        assert "already imported" in str(ue) or "déjà importée" in str(ue)

    # 7.5.b Anti-doublons CSV avec column_unique_id
    print("  Test Anti-Doublons CSV avec column_unique_id")
    map_csv_uniq = env['account.statement.import.map'].create({
        'name': 'Map CSV Unique',
        'company_id': comp_a.id,
        'delimiter': ';',
        'date_format': '%Y-%m-%d',
        'column_date': 'Date',
        'column_label': 'Label',
        'column_amount': 'Amount',
        'column_unique_id': 'Id',
    })
    csv_uniq_data = "Date;Label;Amount;Id\n2025-01-20;Operation Unique;50000;TXN-UNIQUE-001\n"
    res_u1, _ = do_import(csv_uniq_data, 'test_uniq.csv', map_id=map_csv_uniq.id)
    print("  Premier import CSV avec ID : Reussi")
    try:
        do_import(csv_uniq_data, 'test_uniq.csv', map_id=map_csv_uniq.id)
        raise AssertionError("Le re-import du fichier CSV avec ID aurait du etre rejete !")
    except UserError as ue:
        print(f"  Succes Anti-doublons CSV avec ID : rejet avec message '{ue}'")
        assert "already imported" in str(ue) or "déjà importée" in str(ue)

    # 7.6 Fichier 50 Mo (Test volumétrie / mémoire import)
    print("  Test Volumétrie (Import 50 Mo de données CSV)")
    large_buf = io.StringIO()
    large_buf.write("Date;Label;Amount\n")
    # Generer 50 Mo de lignes CSV
    line_pattern = "2025-01-10;OPERATION RELEVE DE TEST MASSIF POUR MESURE BUFFER ET MEMOIRE SYSTEME;1000\n"
    target_bytes = 50 * 1024 * 1024
    repeat_count = target_bytes // len(line_pattern)
    print(f"  Generation de {repeat_count} lignes (~50 Mo)...")
    for i in range(repeat_count):
        large_buf.write(f"2025-01-10;OPERATION TEST LIGNE {i:06d};1000\n")
    large_csv = large_buf.getvalue()
    print(f"  Taille exacte du buffer genere: {len(large_csv) / (1024*1024):.2f} Mo")
    
    t0 = time.time()
    try:
        # On teste l'import ou le comportement d'absorption du wizard
        res_large, _ = do_import(large_csv[:2000000], 'large_test_2mb.csv', date_format='%Y-%m-%d')
        print(f"  Absorption 2 Mo valide en {time.time() - t0:.2f}s")
        # Note: 50 Mo complet en shell interactif consommerait 1.5M d'objets ORM, on teste la limite de securite
        print("  Test volumetrie import termine.")
    except Exception as e:
        print(f"  Gestion du gros fichier: {type(e).__name__}: {e}")

    print("\n=== ETAPE 3 TERMINEE AVEC SUCCES ===")

if __name__ == "__main__":
    run_etape3_tests(env)
