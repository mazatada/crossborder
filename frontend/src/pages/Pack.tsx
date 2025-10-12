import { useState } from "react";
import { api } from "../api";
import { useJob } from "../hooks/useJob";
import { Stack, TextField, Button, Typography, Alert, MenuItem, Select } from "@mui/material";

export default function Pack() {
  const [traceId,setTraceId]=useState("LAW-2025-10-10-XYZ");
  const [hsCode,setHsCode]=useState("1905.90");
  const [hsUom,setHsUom]=useState("kg");
  const [invoiceUom,setInvoiceUom]=useState("kg");
  const [jobId,setJobId]=useState<string>();
  const {data} = useJob(jobId);
  const [error,setError]=useState<string>();

  const generate = async ()=>{
    setError(undefined);
    try{
      const res = await api.post("/docs/clearance-pack",
        { traceId, hs_code: hsCode, required_uom: hsUom, invoice_uom: invoiceUom },
        { headers: { "Idempotency-Key": crypto.randomUUID() }});
      setJobId(res.data.job_id);
    }catch(e:any){ setError(e.response?.data?.error?.message || e.message) }
  }

  return (
    <Stack spacing={2} sx={{p:2}}>
      <Typography variant="h5">Clearance Pack</Typography>
      {error && <Alert severity="error">{error}</Alert>}
      <Stack direction="row" spacing={2}>
        <TextField size="small" label="Trace ID" value={traceId} onChange={e=>setTraceId(e.target.value)} />
        <TextField size="small" label="HS Code" value={hsCode} onChange={e=>setHsCode(e.target.value)} />
        <Select size="small" value={hsUom} onChange={e=>setHsUom(e.target.value as string)}>
          <MenuItem value="kg">kg</MenuItem><MenuItem value="l">l</MenuItem><MenuItem value="No.">No.</MenuItem>
        </Select>
        <Select size="small" value={invoiceUom} onChange={e=>setInvoiceUom(e.target.value as string)}>
          <MenuItem value="kg">kg</MenuItem><MenuItem value="l">l</MenuItem><MenuItem value="No.">No.</MenuItem>
        </Select>
        <Button variant="contained" onClick={generate}>Generate ZIP</Button>
      </Stack>
      {data?.artifacts?.length ? <Alert severity="success">ZIP ready: {data.artifacts[0].media_id}</Alert> : null}
    </Stack>
  );
}
