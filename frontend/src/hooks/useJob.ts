import { useEffect, useState } from "react";
import { api } from "../api";

export function useJob(jobId?: string) {
  const [data,setData] = useState<any>(null);
  const [loading,setLoading] = useState(!!jobId);
  useEffect(()=>{
    if(!jobId) return;
    let mounted = true;
    const poll = async () => {
      const res = await api.get(`/jobs/${jobId}`);
      if(!mounted) return;
      setData(res.data);
      if(res.data.status && !["completed","failed","submitted"].includes(res.data.status)) {
        setTimeout(poll, 1200);
      }
    };
    setLoading(true); poll().finally(()=>setLoading(false));
    return ()=>{ mounted=false; };
  },[jobId]);
  return {data,loading};
}
