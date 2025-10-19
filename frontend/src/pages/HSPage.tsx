import { useState } from 'react';
import { Button, TextField, Typography, Paper, Table, TableHead, TableRow, TableCell, TableBody, Stack } from '@mui/material';
import { classifyHS } from '../api';
import type { HSResponse } from '../types';

export default function HSPage() {
  const [name, setName] = useState('Dorayaki');
  const [res, setRes] = useState<HSResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const onClassify = async () => {
    setErr(null);
    try {
      const payload = {
        product: { name, category: 'confectionery', process: ['baked'], ingredients: [{ id: 'ing_wheat_flour' }] }
      };
      setRes(await classifyHS(payload));
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message ?? 'classification failed');
    }
  };

  return (
    <Stack spacing={2}>
      <Typography variant="h5">HS分類（最小）</Typography>
      <Stack direction="row" spacing={2}>
        <TextField label="製品名" value={name} onChange={e=>setName(e.target.value)} />
        <Button variant="contained" onClick={onClassify}>分類を実行</Button>
      </Stack>
      {err && <Typography color="error">{err}</Typography>}
      {res && (
        <Paper>
          <Table size="small">
            <TableHead><TableRow>
              <TableCell>HS Code</TableCell><TableCell>Conf.</TableCell><TableCell>UoM</TableCell><TableCell>根拠</TableCell>
            </TableRow></TableHead>
            <TableBody>
              {res.hs_candidates.map((c,i)=>(
                <TableRow key={i}>
                  <TableCell>{c.code}</TableCell>
                  <TableCell>{Math.round(c.confidence*100)}%</TableCell>
                  <TableCell>{c.required_uom}</TableCell>
                  <TableCell>{c.rationale.join('; ')}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Stack>
  );
}
