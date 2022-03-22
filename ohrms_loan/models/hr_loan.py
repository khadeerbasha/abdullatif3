# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)

class HrLoan(models.Model):
	_name = 'hr.loan'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Loan Request"
	
	@api.depends('loan_lines.paid','loan_lines.amount')
	def _compute_loan_amount(self):
		for loan in self:
			total_paid = 0.0
			total_amt = 0.0
			for line in loan.loan_lines:
				total_amt += line.amount
				if line.paid:
					total_paid += line.amount
			loan.update({
				'total_amount': total_amt,
				'total_paid_amount': total_paid,
				'balance_amount': total_amt - total_paid,
			})

	@api.model
	def default_get(self, field_list):
		result = super(HrLoan, self).default_get(field_list)
		if result.get('user_id'):
			ts_user_id = result['user_id']
		else:
			ts_user_id = self.env.context.get('user_id', self.env.user.id)
		result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', ts_user_id)], limit=1).id
		return result

	'''def _compute_loan_amount(self):
		for loan in self:
			total_paid = 0.0
			for line in loan.loan_lines:
				if line.paid:
					_logger.info("Confirm Ids %s"%(line.paid))
					total_paid += line.amount
					_logger.info("Confirm Ids %s"%(total_paid))
					#print("TTTTTTTTTTTTTTTTTTTTTT",total_paid)
					#_logger.info("Confirm Ids %s"%(total_paid))
			balance_amount = loan.loan_amount - total_paid
			loan.total_paid_amount = total_paid
			loan.total_amount = loan.loan_amount
			loan.balance_amount = loan.loan_amount - total_paid'''
			

	name = fields.Char(string="Loan Name", readonly=True, help="Name of the loan")
	multi_loan = fields.Boolean(string="Multi Loan")
	date = fields.Date(string="Date", default=fields.Date.today(), readonly=True, help="Date")
	employee_id = fields.Many2one('hr.employee', string="Employee", required=True, help="Employee")
	department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
									string="Department", help="Employee")
	installment = fields.Integer(string="No Of Installments", default=1, help="Number of installments")
	payment_date = fields.Date(string="Payment Start Date", required=True, default=fields.Date.today(), help="Date of "
																											 "the "
																											 "paymemt")
	loan_lines = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
	company_id = fields.Many2one('res.company', 'Company', readonly=True, help="Company",
								 default=lambda self: self.env.user.company_id,
								 states={'draft': [('readonly', False)]})
	currency_id = fields.Many2one('res.currency', string='Currency', required=True, help="Currency",
								  default=lambda self: self.env.user.company_id.currency_id)
	job_position = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position",
								   help="Job position")
	loan_amount = fields.Float(string="Loan Amount", required=True, help="Loan amount")
	total_amount = fields.Monetary(string="Total Amount", store=True, readonly=True, compute='_compute_loan_amount',
								help="Total loan amount")
	balance_amount = fields.Monetary(string="Balance Amount", store=True, compute='_compute_loan_amount', help="Balance amount")
	total_paid_amount = fields.Monetary(string="Total Paid Amount", store=True, compute='_compute_loan_amount',
									 help="Total paid amount")
	loan_journal_count = fields.Integer(string='Journal Count', compute='_get_journal_count', store=False)

	def _get_journal_count(self):
		for record in self:
			record.loan_journal_count = self.env['account.move'].search_count([('ref', '=', record.name)])

	def open_entries(self):
		return {
		    'name': _('Journal Entries'),
		    'view_mode': 'tree,form',
		    'res_model': 'account.move',
		    'view_id': False,
		    'type': 'ir.actions.act_window',
		    "domain": [('ref','=', self.name)]
		}

	state = fields.Selection([
		('draft', 'Draft'),
		('waiting_approval_1', 'Submitted'),
		('approve', 'Approved'),
		('refuse', 'Refused'),
		('cancel', 'Canceled'),
	], string="State", default='draft', track_visibility='onchange', copy=False, )
    
	@api.constrains('multi_loan')
	def _validate_multi_loan(self):
		loan_count = self.env['hr.loan'].search_count([('employee_id', '=', self.employee_id.id), ('state', '=', 'approve'),('balance_amount', '!=', 0)])
		if loan_count:
			if self.multi_loan == False:
				raise ValidationError(_("The employee has already a pending installment."))
    
	@api.model
	def create(self, values):
		'''loan_count = self.env['hr.loan'].search_count(
			[('employee_id', '=', values['employee_id']), ('state', '=', 'approve'),
			 ('balance_amount', '!=', 0)])
		print('TTTTTTTTTTTTTTTTTTTTTT',loan_count)
		if loan_count:
			#if values.get('multi_loan', False) == False:
			raise ValidationError(_("The employee has already a pending installment"))
		else:'''
		values['name'] = self.env['ir.sequence'].get('hr.loan.seq') or ' '
		res = super(HrLoan, self).create(values)
		return res

	def compute_installment(self):
		"""This automatically create the installment the employee need to pay to
		company based on payment start date and the no of installments.
			"""
		for loan in self:
			loan.loan_lines.unlink()
			date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
			amount = loan.loan_amount / loan.installment
			for i in range(1, loan.installment + 1):
				self.env['hr.loan.line'].create({
					'date': date_start,
					'amount': amount,
					'employee_id': loan.employee_id.id,
					'loan_id': loan.id})
				date_start = date_start + relativedelta(months=1)
			loan._compute_loan_amount()
		return True

	def action_refuse(self):
		return self.write({'state': 'refuse'})

	def action_submit(self):
		for record in self:
			lines_amount = sum(record.loan_lines.mapped('amount'))
			for tab in record.loan_lines:
				if tab.amount < 0.0:
					raise ValidationError('One of the Installment Amount is in Negative Value')
			if record.loan_amount != lines_amount:
				raise ValidationError('Loan Amount must be equal to Total Amount')
			if not self.loan_lines:
				raise ValidationError('You must Schedule Loan before Submit')       
		self.write({'state': 'waiting_approval_1'})

	def action_cancel(self):
		self.write({'state': 'cancel'})

	def action_approve(self):
		for data in self:
			lines_amount = sum(data.loan_lines.mapped('amount'))
			for tab in data.loan_lines:
				if tab.amount < 0.0:
					raise ValidationError('One of the Installment Amount is in Negative Value')
			if data.loan_amount != lines_amount:
				raise ValidationError('Loan Amount must be equal to Total Amount')
			if not data.loan_lines:
				raise ValidationError(_("Please Compute installment"))
			else:
				self.write({'state': 'approve'})

	def unlink(self):
		for loan in self:
			if loan.state not in ('draft', 'cancel'):
				raise UserError(
					'You cannot delete a loan which is not in draft or cancelled state')
		return super(HrLoan, self).unlink()


class InstallmentLine(models.Model):
	_name = "hr.loan.line"
	_description = "Installment Line"

	date = fields.Date(string="Payment Date", required=True, help="Date of the payment")
	employee_id = fields.Many2one('hr.employee', string="Employee", help="Employee")
	amount = fields.Float(string="Amount", required=True, help="Amount")
	paid = fields.Boolean(string="Paid", help="Paid")
	loan_id = fields.Many2one('hr.loan', string="Loan Ref.", help="Loan")
	payslip_id = fields.Many2one('hr.payslip', string="Payslip Ref.", help="Payslip")
	
	def unlink(self):
		for loan in self:
			if loan.paid:
				raise UserError('You cannot delete a Paid Installment')
		return super(InstallmentLine, self).unlink()


class HrEmployee(models.Model):
	_inherit = "hr.employee"

	def _compute_employee_loans(self):
		"""This compute the loan amount and total loans count of an employee.
			"""
		self.loan_count = self.env['hr.loan'].search_count([('employee_id', '=', self.id)])

	loan_count = fields.Integer(string="Loan Count", compute='_compute_employee_loans')

	def get_loan_deduction(self,employee, date_from, date_to):
		
		loan_obj = self.env['hr.loan']
		loan_amount = 0.00
		history_ids = self.env['hr.loan.line'].search_count([('date', '>=', date_from),('date', '<=', date_to),('employee_id', '=', employee),('paid', '=', False)])
		if history_ids:
			for each in history_ids:
				vals = self.env['hr.loan.line'].browse()
				if vals.loan_id.state == 'approve':
				    loan_amount += vals.amount
				    each.write({'paid': True})
		return loan_amount