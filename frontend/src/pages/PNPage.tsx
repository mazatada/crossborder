import { useState } from 'react';
import {
  Button, TextField, Typography, Grid, Paper, Alert, MenuItem, Stack
} from '@mui/material';
import { createPN } from '../api';
import { useJobPoller } from '../hooks/useJobPoller';

export default function PNPage() {
  const [traceId, setTraceId]   = useState('PN-TEST-001');
  const [name, setName]         = useState('Dorayaki');
  const [desc, setDesc]         = useState('Sweet red-bean pancake');
  const [origin, setOrigin]     = useState('JP');
  const [mode, setMode]         = useState<'AIR'|'EXPRESS'|'SEA'>('AIR');
  const [poe, setPoe]           = useState('LAX');
  const [arrival, setArrival]   = useState('2025-10-20');
  const [jobId, setJobId]       = useState<string>();

  const job = useJobPoller(jobId);

  const submit = async () => {
    const payload = {
      traceId,
      product: { name, description: desc, hs_code: '1905.90', origin_country: origin },
      logistics: { mode, carrier: 'DHL', port_of_entry: poe, arrival_date: arrival },
      importer: { name: 'Importer Inc.' },
      consignee: { name: 'Consignee LLC' },
      label_media_id: 'media_dummy'
    };
    const id = await createPN(payload);
    setJobId(id);
  };

  return (
    <Stack spacing={2}>
      <Typography variant="h5">PN申請</Typography>

      <Paper elevation={1} sx={{ p: 2 }}>
        <Grid container spacing={2}>
          {/* トレース */}
          <Grid item xs={12} sm={6} md={4}>
            <TextField
              label="Trace ID"
              value={traceId}
              onChange={(e)=>setTraceId(e.target.value)}
              fullWidth
            />
          </Grid>

          {/* 製品名 */}
          <Grid item xs={12} sm={6} md={4}>
            <TextField
              label="Product Name"
              value={name}
              onChange={(e)=>setName(e.target.value)}
              fullWidth
            />
          </Grid>

          {/* 説明（長め） */}
          <Grid item xs={12} md={8}>
            <TextField
              label="Description"
              value={desc}
              onChange={(e)=>setDesc(e.target.value)}
              fullWidth
              multiline
              minRows={2}
            />
          </Grid>

          {/* 原産国 */}
          <Grid item xs={12} sm={6} md={2}>
            <TextField
              label="Origin (ISO2)"
              value={origin}
              onChange={(e)=>setOrigin(e.target.value.toUpperCase())}
              inputProps={{ maxLength: 2 }}
              helperText="例: JP / US"
              fullWidth
            />
          </Grid>

          {/* Mode */}
          <Grid item xs={12} sm={6} md={2}>
            <TextField
              select
              label="Mode"
              value={mode}
              onChange={(e)=>setMode(e.target.value as any)}
              fullWidth
            >
              <MenuItem value="AIR">AIR</MenuItem>
              <MenuItem value="EXPRESS">EXPRESS</MenuItem>
              <MenuItem value="SEA">SEA</MenuItem>
            </TextField>
          </Grid>

          {/* Port of Entry */}
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              label="Port of Entry"
              value={poe}
              onChange={(e)=>setPoe(e.target.value.toUpperCase())}
              helperText="IATA/UNLOCODE 例: LAX"
              fullWidth
            />
          </Grid>

          {/* 到着日 */}
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              label="Arrival (YYYY-MM-DD)"
              type="date"
              value={arrival}
              onChange={(e)=>setArrival(e.target.value)}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
          </Grid>

          {/* 送信ボタン行 */}
          <Grid item xs={12}>
            <Stack direction="row" spacing={2} justifyContent="flex-end">
              <Button variant="contained" onClick={submit}>申請</Button>
            </Stack>
          </Grid>
        </Grid>
      </Paper>

      {jobId && <Alert severity="info">Job: {jobId} / Status: {job?.status ?? '...'}</Alert>}
    </Stack>
  );
}
