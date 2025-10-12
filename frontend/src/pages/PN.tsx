import { useState } from "react";
import { api } from "../api";
import { useJob } from "../hooks/useJob";
import { Stack, TextField, Button, Typography, Alert } from "@mui/material";

export default function PN() {
  const [traceId,setTraceId]=useState("LAW-2025-10-10-XYZ");
  const [jobId,setJobId]=useState<string>();
  const {data} = useJob(jobId);
  const [error,setError]=useState<string>();

  const submit = async ()=>{
    setError(undefined);
    try{
      const res = await api.post("/fda/prior-notice", {
        traceId,
        product:{ description:"Sweet baked confectionery (dorayaki)", origin_country:"JP" },
        logistics:{ mode:"air", port_of_entry:"LAX", arrival_date:"2025-10-15", quantity:1000, pkg_type:"carton" },
        importer:{ name:"XYZ LLC" }, consignee:{ name:"XYZ Warehouse" },
        label_media_id:"sha256:dummy"
      }, { headers: { "Idempotency-Key": crypto.randomUUID() }});
      setJobId(res.data.job_id);
    }catch(e:any){
      setError(e.response?.data?.errors?.join(", ") || e.message);
    }
  }

  return (
    <Stack spacing={2} sx={{p:2}}>
      <Typography variant="h5">FDA Prior Notice</Typography>
      {error && <Alert severity="error">{error}</Alert>}
      <Stack direction="row" spacing={2}>
        <TextField size="small" label="Trace ID" value={traceId} onChange={e=>setTraceId(e.target.value)} />
        <Button variant="contained" onClick={submit}>Submit PN</Button>
      </Stack>
      {jobId && <Alert severity="success">Submitted Job: {jobId}</Alert>}
      {data?.artifacts?.length ? <Alert severity="info">Receipt: {data.artifacts[0].media_id}</Alert> : null}
    </Stack>
  );
}
