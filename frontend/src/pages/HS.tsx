import { useState } from "react";
import { api } from "../api";
import { Button, Card, CardContent, Typography, Stack, List, ListItem, ListItemText, TextField } from "@mui/material";
import SignalCard from "../components/SignalCard";

export default function HS() {
  const [traceId,setTraceId]=useState("LAW-2025-10-10-XYZ");
  const [resp,setResp]=useState<any>(null);
  const [status,setStatus]=useState<"green"|"amber"|"red">("amber");
  const classify = async ()=>{
    const res = await api.post("/classify/hs", { product: { name:"Dorayaki", category:"confectionery", process:["baked"], ingredients:[{id:"ing_wheat_flour"}] }});
    setResp(res.data);
    const risk = res.data?.risk_flags;
    setStatus(risk?.ad_cvd || risk?.import_alert ? "red" : (res.data.hs_candidates[0]?.confidence < 0.6 ? "amber" : "green"));
  };
  return (
    <Stack spacing={2} sx={{p:2}}>
      <Typography variant="h5">HS Classification</Typography>
      <SignalCard status={status} reasons={["HS","UoM","PN"]}/>
      <Card><CardContent>
        <Stack direction="row" spacing={2}>
          <TextField label="Trace ID" value={traceId} onChange={e=>setTraceId(e.target.value)} size="small"/>
          <Button variant="contained" onClick={classify}>Classify</Button>
        </Stack>
        {resp && (
          <>
            <Typography sx={{mt:2}} variant="subtitle1">Candidates</Typography>
            <List>
              {resp.hs_candidates.map((c:any,i:number)=>(
                <ListItem key={i} divider>
                  <ListItemText primary={`${c.code} (${Math.round(c.confidence*100)}%)  uom:${c.required_uom||"-"}`}
                                secondary={(c.rationale||[]).join(" / ")}/>
                </ListItem>
              ))}
            </List>
          </>
        )}
      </CardContent></Card>
    </Stack>
  );
}
