import { useCallback, useState } from 'react';
import { workspaceApi } from '../lib/api';
import useApiData from '../hooks/useApiData';
import { ContractSheet } from '../pages/RentalWorkspace';
import ContractForm from './ContractForm';
import Dialog from './Dialog';
import { Loading, Button } from './ui';
import { RetryError } from './EntityUI';
import { AdjustmentDialog, CancelMovementDialog, ChargeDialog, BulkSettlementDialog, OwnerStatementDialog, DocumentDialog, MessageDialog, MoneyOperation, ReceiptDialog, propertyLabel } from './RentalDialogs';

export default function DashboardContractSheet({ row, field, filters, onClose }) {
  const year=Number(filters.year),month=Number(filters.month),currency=filters.currency;
  const [contractId,setContractId]=useState(row.contract_ids[0]);
  const [edit,setEdit]=useState(null),[dialog,setDialog]=useState(null);
  const loader=useCallback((signal)=>workspaceApi({year,month,currency},signal),[year,month,currency]);
  const {data,loading,error,reload}=useApiData(loader);
  const saved=()=>{setEdit(null);setDialog(null);reload();};
  const selected=data?.contracts.find((contract)=>contract.id===contractId);
  const labels={collections:'Cobro recibido',pending:'Alquiler pendiente',administration_fees:'Honorarios',expenses:'Gasto'};
  if(loading||error||!selected)return <Dialog title="Ficha completa del cliente" size="xl" onClose={onClose}><div className="p-6">{loading?<Loading label="Abriendo ficha completa…"/>:error?<RetryError error={error} onRetry={reload}/>:<p>No se encontró el contrato relacionado con este movimiento.</p>}</div></Dialog>;
  return <>
    <ContractSheet key={selected.id} contract={selected} data={data} year={year} month={month} onClose={onClose} onEdit={()=>setEdit({contract:selected})} onDialog={setDialog} onRefresh={reload} consultedMovement={{...row,metricLabel:labels[field]}} contractPicker={row.contract_ids.length>1?<div className="flex flex-wrap gap-2" aria-label="Contratos relacionados">{row.contract_ids.map((id)=><Button key={id} variant={id===contractId?'primary':'secondary'} onClick={()=>setContractId(id)}>Contrato #{id} · {propertyLabel(data.properties.find((property)=>property.id===data.contracts.find((contract)=>contract.id===id)?.property_id))}</Button>)}</div>:null}/>
    {edit&&data&&<ContractForm contract={edit.contract} properties={data.properties} people={data.people} contracts={data.contracts} onClose={()=>setEdit(null)} onSaved={saved}/>}
    {dialog&&['payment','transfer','settlement'].includes(dialog.kind)&&<MoneyOperation {...dialog} year={year} month={month} currency={currency} onClose={()=>setDialog(null)} onSaved={saved}/>}
    {dialog?.kind==='cancel'&&<CancelMovementDialog {...dialog} onClose={()=>setDialog(null)} onSaved={saved}/>}
    {dialog?.kind==='charge'&&<ChargeDialog {...dialog} year={dialog.year||year} month={dialog.month||month} onClose={()=>setDialog(null)} onSaved={saved}/>}
    {dialog?.kind==='adjustment'&&<AdjustmentDialog {...dialog} onClose={()=>setDialog(null)} onSaved={saved}/>}
    {dialog?.kind==='message'&&<MessageDialog {...dialog} year={dialog.year||year} month={dialog.month||month} onClose={()=>setDialog(null)}/>}
    {dialog?.kind==='receipt'&&<ReceiptDialog {...dialog} year={dialog.year||year} month={dialog.month||month} currency={currency} onClose={()=>setDialog(null)}/>}
    {dialog?.kind==='bulkSettlement'&&data&&<BulkSettlementDialog {...dialog} data={data} year={year} month={month} currency={currency} onClose={()=>setDialog(null)} onSaved={saved}/>}
    {dialog?.kind==='ownerStatement'&&data&&<OwnerStatementDialog {...dialog} properties={data.properties} year={year} month={month} currency={currency} onClose={()=>setDialog(null)}/>}
    {dialog?.kind==='document'&&<DocumentDialog {...dialog} year={dialog.year||year} month={dialog.month||month} onClose={()=>setDialog(null)} onSaved={saved}/>}
  </>;
}
