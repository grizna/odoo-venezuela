#!/usr/bin/python
# -*- encoding: utf-8 -*-
###########################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#    Copyright (C) OpenERP Venezuela (<http://openerp.com.ve>).
#    All Rights Reserved
###############Credits######################################################
#    Coded by: Humberto Arocha           <humberto@openerp.com.ve>
#              Angelica Barrios          <angelicaisabelb@gmail.com>
#              María Gabriela Quilarque  <gabrielaquilarque97@gmail.com>
#              Javier Duran              <javier@vauxoo.com>             
#    Planified by: Nhomar Hernandez
#    Finance by: Helados Gilda, C.A. http://heladosgilda.com.ve
#    Audited by: Humberto Arocha humberto@openerp.com.ve
#############################################################################
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################
from osv import osv
from osv import fields
from tools.translate import _
import decimal_precision as dp
import time
######################Soporte de Pago##########################

class voucher_pay_support(osv.osv):
    _description = "voucher_pay_support"
    _name='voucher.pay.support'

    def _get_company_currency(self, cr, uid, ids, field_name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            result[rec.id] = (rec.company_id.currency_id.id,rec.company_id.currency_id.code)
        return result
      
    def _check_duplicar(self,cr,uid,ids):
        obj_soporte = self.browse(cr,uid,ids[0])
        cr.execute('select a.check_note_id  from voucher_pay_support a   where a.check_note_id=%d'%(obj_soporte.check_note_id))
        lista=cr.fetchall()
        #comprension de lista
        bandera=([x[0] for x in lista if x[0] == obj_soporte.check_note_id.id])
        #bandera devuelve una lista de las ocurrencias
        if  len(bandera)>1 :
            return False
        return True
    
    _columns={
        'name':fields.char('Acknowledgment of receipt',size=256, required=False, readonly=False ,
                    states={
                    'draft':[('readonly',False)],
                    'open':[('readonly',True)],
                    'done':[('readonly',True)],
                    'cancel':[('readonly',True)]}),
        'accounting_bank_id':fields.many2one('res.partner.bank','Bank Account', readonly=True),
        'check_note_id': fields.many2one('check.note', 'Check Note', readonly=True, states={'draft':[('readonly',False)]} ,required=True, domain="[('accounting_bank_id','=',accounting_bank_id)]"),
        'bank_id':fields.related('check_note_id','bank_id',type='many2one',relation='res.bank',string='Bank', store=True, readonly=True),
        'min_lim':fields.related('bank_id','min_lim',type='integer',relation='res.bank',string='Min. Limit',readonly=True,store=False),
        'max_lim':fields.related('bank_id','max_lim',type='integer',relation='res.bank',string='Max Limit',readonly=True,store=False),
        'company_id': fields.many2one('res.company', 'Company', required=True , readonly=True),
        'expiry':fields.related('company_id','expiry', type='integer',relation='res.company',string='Expiry Days',readonly=True,store=True),
        'payee_id':fields.many2one('res.partner.address','Beneficiary',required=False, readonly=True),
        'partner_id':fields.many2one('res.partner','Contrapartida',required=True, readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('open','Open'),
            ('done','Done'),
            ('cancel','Cancel'),
            ],'State', select=True, readonly=True, help="State Voucher Check Note"),
        'wire':fields.char('Transfer',size=26),
        'type': fields.selection([
            ('check','Cheque'),
            ('wire','Transferencia'),
            ],'Type', required=True, select=True , readonly=True),
        'amount':fields.float('Amount', readonly=True, digits_compute= dp.get_precision('Bank')),
        'date':fields.date('Issued Date', readonly=True),
        'cancel_check_note': fields.selection([
            ('print','Print Error'),
            ('perdida','Loss or misplacement'),
            ('dan_fis','Physical damage'),
            ('pago','Payment is not made'),
            ('devuelto','Returned check'),
            ('caduco','Expired'),
            ('otros','Other'),
            ],'Reason for Cancellation', select=True, readonly=True,
                        states={'draft':[('readonly',False)],
                        'open':[('readonly',False)],
                        'cancel':[('readonly',True)],
                        'done':[('readonly',True)]}),
        'notes':fields.char('Note',size=256, required=False, readonly=False ,
                        states={'draft':[('readonly',False)],
                        'open':[('readonly',False)],
                        'cancel':[('readonly',True)],
                        'done':[('readonly',True)]}),
        'return_voucher_id':fields.many2one('account.voucher','Cancellation Voucher', readonly=True), 
        'account_voucher_id':fields.related('check_note_id','account_voucher_id',type='many2one',relation='account.voucher',string='Origin Voucher',store=True,readonly=True),
        'account_voucher_transitory_id':fields.many2one('account.voucher','Transitory Voucher', readonly=True),

     }

    _constraints = [
        (_check_duplicar, 'Warning ! You can not duplicate this document', ['check_note_id']),
    ]


    def onchange_type(self, cursor, user, ids, type):
        if type:
            return {'value': {'wire': False,
                              'check_note_id': False,}}
        return False


    _defaults = {
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
        'type': lambda *a: 'check',
        'state': lambda *a: 'draft',
    }


    def get_retirado(self, cr, uid, ids, context={}):
        soporte = self.browse(cr,uid,ids)
        for i in soporte:
            if i.cancel_check_note or i.notes:
                raise osv.except_osv(_('Alert !'), _('Remove the reason for cancellation'))
            else:
                if i.name:
                    self.write(cr,uid,i.id,{'state' : 'open', 'name':i.name })
                else:
                    raise osv.except_osv(_('Alert !'), _('Enter the acknowledgment'))
        return True

    def get_realizado(self, cr, uid, ids, context={}):
        soporte = self.browse(cr,uid,ids)
        for i in soporte:
            #se cambia el documento a estado done
            self.write(cr,uid,i.id,{'state' : 'done' })     
            #se cambia el cheque a estado cobrado= done y la fecha de cobro
            self.pool.get('check.note').write(cr,uid,i.check_note_id.id,{'state' : 'done', 'date_done':time.strftime('%Y-%m-%d')})
            #se realiza el asiento contable, si existen cuentas transitorias
            transitory=self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.transitory
            if transitory== True:
                cuenta_transitoria=i.accounting_bank_id.trans_account_id
                if cuenta_transitoria: # se llama al metodo que crear el soporte de pago
                    self.create_voucher(cr, uid, ids,i, context)
                else:
                    raise osv.except_osv(_('Alert !'), _('You must enter Account Bank Transitional: %s')%(i.accounting_bank_id.bank_id.name))
        return True


    def create_voucher(self, cr, uid, ids, soporte, context=None):
        this = self.browse(cr, uid, ids[0])
        created_account_voucher = []
        account_voucher=self.pool.get('account.voucher')
        account_voucher_line=self.pool.get('account.voucher.line')
        obj_acount_voucher=soporte.account_voucher_id
        name="COBRO DEL CHEQUE POR CONCEPTO %s"%(obj_acount_voucher.name)
        narration="COBRO DEL CHEQUE POR CONCEPTO %s"%(obj_acount_voucher.narration)


        #se crea el nuevo documento de comprobante diario
        account_voucher_id=account_voucher.create(cr, uid,{
                        'name': name,
                        'type': 'cont_voucher',
                        'date': time.strftime('%Y-%m-%d'),
                        'journal_id':obj_acount_voucher.journal_id.id,
                        'account_id':soporte.accounting_bank_id.bank_account_id.id,
                        'period_id':obj_acount_voucher.period_id.id,
                        'narration': narration,
                        'currency_id':obj_acount_voucher.currency_id.id,
                        'company_id': obj_acount_voucher.company_id.id,
                        'state':   'draft',
                        'amount':obj_acount_voucher.amount,
                        'reference_type': 'none',
                        'partner_id': obj_acount_voucher.partner_id.id,
                        'payee_id': obj_acount_voucher.payee_id.id
        },context=None)

        account_voucher_line_id=account_voucher_line.create(cr, uid,{
                        'voucher_id':account_voucher_id,
                        'name': "Transitorio",
                        'account_id': soporte.accounting_bank_id.trans_account_id.id,
                        'amount': obj_acount_voucher.amount,
                        'type': 'dr',
        },context=None)
        self.write(cr, uid, [soporte.id], {'account_voucher_transitory_id': account_voucher_id})
        return True


    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if not context:
            context={}
        return super(voucher_pay_support, self).write(cr, uid, ids, vals, context=context)

voucher_pay_support()



class account_voucher(osv.osv):
    _inherit="account.voucher"
    _columns={
        'check_note_ids': fields.one2many('check.note', 'account_voucher_id', 'Checks',readonly=False, required=False),
        'payee_id':fields.many2one('res.partner.address','Beneficiary',required=False, readonly=False),
        'journal_id':fields.many2one('account.journal', 'Journal', required=False, readonly=True, states={'draft':[('readonly',False)]}),
        'account_id':fields.many2one('account.account', 'Account', required=False, readonly=True, states={'draft':[('readonly',False)]}, domain=[('type','<>','view')]),
        'voucher_pay_support_id':fields.many2one('voucher.pay.support', 'Payment Order', required=False, readonly=True),
    }
account_voucher()

class VoucherLine(osv.osv):
    _inherit = 'account.voucher.line'
    _columns={
        'invoice_id':fields.many2one('account.invoice', 'Invoice', required=False, readonly=False),
        'voucher_id':fields.many2one('account.voucher', 'Voucher', required=0, ondelete='set null'),
    }
    _defaults = {
        'type': lambda *a: 'dr'
    }

    def onchange_invoice_id(self, cr, uid, ids, invoice_id, context={}):
        res = {}
        lines = []
#        if 'lines' in self.voucher_context:
#            lines = [x[2] for x in self.voucher_context['lines'] if x[2]]

        if not invoice_id:
            res = {
                'value':{ }
            }
        else:
            invoice_obj = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context)
            residual = invoice_obj.residual
#            same_invoice_amounts = [x['amount'] for x in lines if x['invoice_id']==invoice_id]
#            residual -= sum(same_invoice_amounts)
            res = {
                'value' : {'amount':residual}
            }
        return res

#    def onchange_line_account(self, cr, uid, ids, account_id, type, type1):
#        if not account_id:
#            return {'value' : {'account_id' : False, 'type' : False ,'amount':False}}
#        obj = self.pool.get('account.account')
#        acc_id = False
#        balance=0
#        print "lo que tiene type1 essssssssssssssssss",type1
#        if type1 in ('rec_voucher','bank_rec_voucher', 'journal_voucher'):
#            print "paso1"
#            acc_id = obj.browse(cr, uid, account_id)
#            balance = acc_id.credit
#            type = 'cr'
#        elif type1 in ('pay_voucher','bank_pay_voucher','cont_voucher'):
#            print "paso2"
#            acc_id = obj.browse(cr, uid, account_id)
#            balance = acc_id.debit
#            type = 'dr'
#        elif type1 in ('journal_sale_vou') : 
#            print "paso3"
#            acc_id = obj.browse(cr, uid, account_id)
#            balance = acc_id.credit
#            type = 'dr'
#        elif type1 in ('journal_pur_voucher') : 
#            print "paso4"
#            acc_id = obj.browse(cr, uid, account_id)
#            balance = acc_id.debit
#            type = 'cr'
#        return {
#            'value' : {'type' : type, 'amount':balance}
#        } 

    def onchange_line_account(self, cr, uid, ids, account_id, type, type1):
        if not account_id:
            return {'value' : {'account_id' : False, 'type' : False ,'amount':False}}
        obj = self.pool.get('account.account')
        acc_id = False
        balance=0
        if type in ('rec_voucher','bank_rec_voucher','journal_voucher'):
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.credit
            type = 'cr'
        elif type in ('pay_voucher','bank_pay_voucher','cont_voucher'):
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.debit
            type = 'dr'
        elif type in ('journal_sale_vou') :
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.credit
            type = 'dr'
        elif type in ('journal_pur_voucher'):
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.debit
            type = 'cr'
        return {
            'value' : {'type' : type, 'amount':balance}
        }


VoucherLine()
