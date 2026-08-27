import { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../services/api';
import { useLayout } from '../context/LayoutContext';

const SERVICES = [
  { id: 'insurance', label: 'Insurance' },
  { id: 'fitness', label: 'Fitness' },
  { id: 'puc', label: 'PUC' },
  { id: 'tax', label: 'Tax' },
  { id: 'permit', label: 'Permit' },
  { id: 'license', label: 'License' },
];

const categoryForService = {
  insurance: 'insurance',
  fitness: 'fitness',
  puc: 'puc',
  tax: 'tax',
  permit: 'permit',
  license: 'license',
};

const serviceDates = {
  insurance: ['insurance_start', 'insurance_end'],
  fitness: ['fitness_start', 'fitness_end'],
  puc: ['puc_start', 'puc_end'],
  tax: ['tax_start', 'tax_end'],
  permit: ['permit_start', 'permit_end'],
  license: ['license_start', 'license_end'],
};

const serviceDetailFields = {
  insurance: ['company_name', 'policy_type', 'policy_number', 'insurance_start', 'insurance_end'],
  fitness: ['fitness_start', 'fitness_end'],
  puc: ['puc_start', 'puc_end'],
  tax: ['tax_start', 'tax_end'],
  permit: ['permit_start', 'permit_end'],
  license: ['license_type', 'license_number', 'license_dob', 'license_start', 'license_end'],
};

const INDIAN_MOBILE_REGEX = /^(?:\+?91[\s-]?)?[6-9]\d{9}$/;

const addMonths = (dateStr, months) => {
  if (!dateStr) return '';
  const [y, m, d] = dateStr.split('-').map(Number);
  const targetMonth = new Date(y, m - 1 + months, 1);
  const lastDay = new Date(targetMonth.getFullYear(), targetMonth.getMonth() + 1, 0).getDate();
  const day = Math.min(d, lastDay);
  const yy = targetMonth.getFullYear();
  const mm = String(targetMonth.getMonth() + 1).padStart(2, '0');
  const dd = String(day).padStart(2, '0');
  return `${yy}-${mm}-${dd}`;
};

// Auto-filled expiries land one day early (e.g. start 02/08/2026 -> expiry 01/02/2027)
const minusOneDay = (dateStr) => {
  if (!dateStr) return '';
  const [y, m, d] = dateStr.split('-').map(Number);
  const previousDay = new Date(y, m - 1, d - 1);
  const yy = previousDay.getFullYear();
  const mm = String(previousDay.getMonth() + 1).padStart(2, '0');
  const dd = String(previousDay.getDate()).padStart(2, '0');
  return `${yy}-${mm}-${dd}`;
};

function FormCard({ title, description, children }) {
  return (
    <section className="card customer-form-card">
      <div className="card-header customer-card-header">
        <div>
          <h2 className="card-title">{title}</h2>
          {description && <p className="card-description">{description}</p>}
        </div>
      </div>
      <div className="card-body">{children}</div>
    </section>
  );
}

function Field({ label, children }) {
  return <div className="form-group"><label className="form-label">{label}</label>{children}</div>;
}

export function CustomerDetailsCard({ register, errors }) {
  return <FormCard title="Customer Details" description="Basic contact and vehicle information">
    <div className="form-grid">
      <Field label="Full Name *"><input className={`form-control ${errors.name ? 'error' : ''}`} placeholder="Customer full name" {...register('name', { required: 'Name is required' })} />{errors.name && <p className="form-error">{errors.name.message}</p>}</Field>
      <Field label="Contact Number *"><input className={`form-control ${errors.contact_number ? 'error' : ''}`} placeholder="+91 98765 43210" {...register('contact_number', { required: 'Contact number is required', validate: (value) => INDIAN_MOBILE_REGEX.test(String(value).trim()) || 'Enter a valid 10-digit mobile number (e.g. 9876543210)' })} />{errors.contact_number && <p className="form-error">{errors.contact_number.message}</p>}</Field>
    </div>
    <div className="form-grid">
      <Field label="Vehicle Number *"><input className={`form-control ${errors.vehicle_number ? 'error' : ''}`} placeholder="GJ-01-AB-1234" {...register('vehicle_number', { required: 'Vehicle number is required' })} />{errors.vehicle_number && <p className="form-error">{errors.vehicle_number.message}</p>}</Field>
      <Field label="Reference Name"><input className="form-control" placeholder="Referral name" {...register('reference_name')} /></Field>
    </div>
  </FormCard>;
}

const SectionCard = ({ title, description, fields, register }) => <FormCard title={title} description={description}>
  <div className="form-grid">
    {fields.map((field) => <Field key={field.name} label={field.label}>{field.options ? <select className="form-control" {...register(field.name)}>{field.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select> : <input type={field.type || 'text'} className="form-control" placeholder={field.placeholder} {...register(field.name)} />}</Field>)}
  </div>
</FormCard>;

export const InsuranceDetailsCard = ({ register }) => <SectionCard register={register} title="Insurance Details" description="Policy and insurance validity" fields={[
  { name: 'company_name', label: 'Company Name', placeholder: 'Insurance company name' }, { name: 'policy_type', label: 'Policy Type', options: [{ value: 'full', label: 'Full' }, { value: 'third_party', label: 'Third Party' }] }, { name: 'policy_number', label: 'Policy Number', placeholder: 'Policy number' },
  { name: 'insurance_start', label: 'Start Date', type: 'date' }, { name: 'insurance_end', label: 'Expiry Date', type: 'date' },
]} />;
export const FitnessDetailsCard = ({ register }) => <SectionCard register={register} title="Fitness Details" description="Vehicle fitness certificate information" fields={[
  { name: 'fitness_start', label: 'Start Date', type: 'date' }, { name: 'fitness_end', label: 'Valid Until', type: 'date' },
]} />;
export const PUCDetailsCard = ({ register }) => <SectionCard register={register} title="PUC Details" description="Pollution Under Control certificate information" fields={[
  { name: 'puc_start', label: 'Start Date', type: 'date' }, { name: 'puc_end', label: 'Valid Until', type: 'date' },
]} />;
export const TaxDetailsCard = ({ register }) => <SectionCard register={register} title="Tax Details" description="Road tax and payment validity" fields={[
  { name: 'tax_start', label: 'Start Date', type: 'date' }, { name: 'tax_end', label: 'Expiry Date', type: 'date' },
]} />;
export const PermitDetailsCard = ({ register }) => <SectionCard register={register} title="Permit Details" description="Vehicle permit validity" fields={[
  { name: 'permit_start', label: 'Start Date', type: 'date' }, { name: 'permit_end', label: 'Expiry Date', type: 'date' },
]} />;
export function LicenseDetailsCard({ register, licenseType, watch, setValue }) {
  const licenseStart = watch('license_start');
  const licenseEnd = watch('license_end');
  const lastAutoEnd = useRef('');
  useEffect(() => {
    if (licenseType !== 'learning' || !licenseStart) return;
    const autoEnd = minusOneDay(addMonths(licenseStart, 6));
    if (licenseEnd === '' || licenseEnd === lastAutoEnd.current) {
      lastAutoEnd.current = autoEnd;
      setValue('license_end', autoEnd);
    }
  }, [licenseType, licenseStart, licenseEnd, setValue]);
  return <FormCard title="License Details" description="Driving or learning license information">
    <div className="form-grid">
      <Field label="License Type"><select className="form-control" {...register('license_type')}><option value="driving">Driving License</option><option value="learning">Learning License</option></select></Field>
      {licenseType === 'driving' && <Field label="License Number"><input className="form-control" placeholder="Driving license number" {...register('license_number')} /></Field>}
      {licenseType === 'driving' && <Field label="Date of Birth"><input type="date" className="form-control" {...register('license_dob')} /></Field>}
      <Field label="Start Date"><input type="date" className="form-control" {...register('license_start')} /></Field>
      <Field label="Expiry Date"><input type="date" className="form-control" {...register('license_end')} /></Field>
    </div>
  </FormCard>;
}

export function PaymentSummaryCard({ register, errors, totalAmount, collectedAmount, isEdit }) {
  const total = Number(totalAmount) || 0;
  const collected = Number(collectedAmount) || 0;
  const pending = Math.max(total - collected, 0);
  return <FormCard title="Payment / Summary" description="Record the service amount and initial payment">
    <div className="form-grid">
      <Field label="Total Amount (₹) *"><input type="number" min="0" step="0.01" className={`form-control ${errors.amount_total ? 'error' : ''}`} placeholder="0.00" {...register('amount_total', { required: 'Amount is required', min: 0 })} />{errors.amount_total && <p className="form-error">{errors.amount_total.message}</p>}</Field>
      <Field label={`Collected Amount (₹)${isEdit ? ' — edits reconcile payment records' : ''}`}><input type="number" min="0" step="0.01" className="form-control" placeholder="0.00" {...register('amount_paid')} /></Field>
      <Field label="Pending Amount (₹)"><input className="form-control payment-pending" value={pending.toFixed(2)} readOnly /></Field>
    </div>
  </FormCard>;
}

export default function AddCustomer() {
  const [selectedServices, setSelectedServices] = useState(['insurance']);
  const navigate = useNavigate();
  const { customerId } = useParams();
  const isEdit = Boolean(customerId);
  const [loadingCustomer, setLoadingCustomer] = useState(isEdit);
  const { setHeaderActions } = useLayout();
  // Original paid amount, so edits that change it can be reconciled against
  // the Payment records via the receipts endpoint.
  const originalPaidRef = useRef(null);

  // Register the "Customer List" action into the shared top bar
  useEffect(() => {
    setHeaderActions(
      <button type="button" className="btn btn-ghost" onClick={() => navigate('/customers')}>Customer List</button>
    );
    return () => setHeaderActions(null);
  }, [setHeaderActions, navigate]);
  const { register, handleSubmit, setValue, reset, watch, formState: { errors, isSubmitting } } = useForm({ defaultValues: { category: 'insurance', license_type: 'driving', amount_total: '', amount_paid: '' } });
  const licenseType = watch('license_type');
  const totalAmount = watch('amount_total');
  const collectedAmount = watch('amount_paid');
  const toggleService = (category) => {
    setSelectedServices((current) => {
      const next = current.includes(category)
        ? current.filter((service) => service !== category)
        : [...current, category];
      setValue('category', next[0] || 'insurance');
      return next;
    });
  };
  const toggleAllServices = () => {
    setSelectedServices((current) => {
      const next = current.length === SERVICES.length ? [] : SERVICES.map((service) => service.id);
      setValue('category', next[0] || 'insurance');
      return next;
    });
  };
  useEffect(() => {
    if (!isEdit) return;
    api.get(`/customers/${customerId}`).then((response) => {
      const customer = response.data.data;
      const customerCategories = customer.categories?.length ? customer.categories : [customer.category];
      const savedDetails = customer.service_details || {};
      const customerServices = customerCategories.flatMap((category) => {
        if (category === 'fitness_puc') return ['fitness', 'puc'];
        return [category];
      });
      reset({
        name: customer.name,
        contact_number: customer.contact_number,
        category: customer.category,
        vehicle_number: customer.vehicle_number || '',
        reference_name: customer.reference_name || '',
        amount_total: customer.amount_total || '',
        amount_paid: customer.amount_paid || '',
        notes: customer.notes || '',
        license_type: 'driving',
        ...Object.fromEntries(customerServices.flatMap((service) => {
          const category = categoryForService[service];
          const [startDateField, endDateField] = serviceDates[service] || [];
          const details = savedDetails[category] || {};
          const fields = serviceDetailFields[service] || [];
          return [
            ...fields.map((field) => [field, details[field] || '']),
            ...(startDateField ? [[startDateField, details[startDateField] || details.start_date || customer.start_date || ''], [endDateField, details[endDateField] || details.end_date || customer.end_date || '']] : []),
          ];
        })),
      });
      setSelectedServices(customerServices);
      originalPaidRef.current = customer.amount_paid;
    }).catch(() => {
      toast.error('Unable to load customer details.');
      navigate('/customers');
    }).finally(() => setLoadingCustomer(false));
  }, [customerId, isEdit, navigate, reset]);
  const submit = async (data) => {
    const { amount_paid } = data;
    const services = selectedServices.length ? selectedServices : ['insurance'];
    const categories = [...new Set(services.map((service) => categoryForService[service]))];
    const service_details = services.reduce((allDetails, service) => {
      const category = categoryForService[service];
      const [startDateField, endDateField] = serviceDates[service];
      const details = Object.fromEntries(serviceDetailFields[service].map((field) => [field, data[field] || null]));
      const current = allDetails[category] || {};
      return {
        ...allDetails,
        [category]: {
          ...current,
          ...details,
          start_date: current.start_date || data[startDateField] || null,
          end_date: current.end_date || data[endDateField] || null,
        },
      };
    }, {});
    const primaryDetails = service_details[categories[0]];
    const payload = {
      name: data.name,
      contact_number: data.contact_number,
      category: categories[0],
      categories,
      service_details,
      vehicle_number: data.vehicle_number,
      reference_name: data.reference_name,
      amount_total: data.amount_total,
      notes: data.notes,
      start_date: primaryDetails.start_date,
      end_date: primaryDetails.end_date,
    };
    try {
      if (isEdit) {
        await api.put(`/customers/${customerId}`, payload);
        const newPaid = Number(amount_paid || 0);
        if (newPaid !== Number(originalPaidRef.current || 0)) {
          // Reconcile the Payment records so paid/pending math stays accurate.
          await api.put(`/receipts/${customerId}/amount`, { amount_paid: newPaid });
        }
        toast.success('Customer updated successfully!');
        navigate('/customers');
        return;
      }
      const response = await api.post('/customers', payload);
      const initialPayment = Number(amount_paid);
      if (response.data?.data?.id && initialPayment > 0) await api.post('/payments', { customer_id: response.data.data.id, amount: initialPayment });
      toast.success('Customer created successfully!');
      navigate('/customers');
    } catch (error) { toast.error(error.response?.data?.message || 'Unable to create customer.'); }
  };

  return <div className="app-content add-customer-page">
    <div className="service-selector" aria-label="Select customer services">
      <div className="service-selector-copy"><span className="service-selector-title">Select services</span><span className="service-selector-help">Choose every service that applies to this customer</span></div>
      <div className="service-options">
        <button type="button" className={`service-option service-option-all ${selectedServices.length === SERVICES.length ? 'checked' : ''}`} onClick={toggleAllServices} aria-pressed={selectedServices.length === SERVICES.length}><span className="service-check">{selectedServices.length === SERVICES.length ? '✓' : ''}</span>All Details</button>
        {SERVICES.map((service) => <label key={service.id} className={`service-option ${selectedServices.includes(service.id) ? 'checked' : ''}`}><input type="checkbox" checked={selectedServices.includes(service.id)} onChange={() => toggleService(service.id)} /><span className="service-check">✓</span>{service.label}</label>)}
      </div>
    </div>
    {loadingCustomer ? <div className="card customer-loading"><span className="spinner" /> Loading customer details…</div> : <form className="customer-master-form" onSubmit={handleSubmit(submit)}>
      <CustomerDetailsCard register={register} errors={errors} />
      <div className="details-panel" key={selectedServices.join('-')}>
        {selectedServices.includes('insurance') && <InsuranceDetailsCard register={register} />}
        {selectedServices.includes('fitness') && <FitnessDetailsCard register={register} />}
        {selectedServices.includes('puc') && <PUCDetailsCard register={register} />}
        {selectedServices.includes('tax') && <TaxDetailsCard register={register} />}
        {selectedServices.includes('permit') && <PermitDetailsCard register={register} />}
        {selectedServices.includes('license') && <LicenseDetailsCard register={register} licenseType={licenseType} watch={watch} setValue={setValue} />}
      </div>
      <PaymentSummaryCard register={register} errors={errors} totalAmount={totalAmount} collectedAmount={collectedAmount} isEdit={isEdit} />
      <div className="customer-form-actions"><button type="button" className="btn btn-ghost" onClick={() => navigate('/customers')}>Cancel</button><button type="submit" className="btn btn-primary" disabled={isSubmitting}>{isSubmitting ? <span className="spinner" /> : isEdit ? 'Save Changes' : 'Save Customer'}</button></div>
    </form>}
  </div>;
}
