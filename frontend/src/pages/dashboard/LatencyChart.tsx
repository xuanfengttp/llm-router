import { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import type { LatencyRecordOut } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { BarChart3, TrendingUp } from 'lucide-react';

interface LatencyChartProps {
  records: LatencyRecordOut[];
}

type ChartMode = 'line' | 'candlestick';

/** ECharts candlestick data point: [timestamp, open, close, low, high] */
type OhlcEntry = [string, number, number, number, number];

interface EChartsSeriesItem {
  name: string;
  type: string;
  data: (string | number)[][] | OhlcEntry[];
  smooth?: boolean;
  symbol?: string;
  symbolSize?: number;
  lineStyle?: Record<string, unknown>;
  itemStyle?: Record<string, unknown>;
}

export function LatencyChart({ records }: LatencyChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const echartsRef = useRef<echarts.ECharts | null>(null);
  const [mode, setMode] = useState<ChartMode>('line');

  useEffect(() => {
    if (!chartRef.current) return;
    if (!echartsRef.current) {
      echartsRef.current = echarts.init(chartRef.current, 'dark');
    }
    return () => { echartsRef.current?.dispose(); echartsRef.current = null; };
  }, []);

  useEffect(() => {
    const chart = echartsRef.current;
    if (!chart) return;

    // Group records by model
    const byModel = new Map<string, LatencyRecordOut[]>();
    for (const r of records) {
      const arr = byModel.get(r.model) || [];
      arr.push(r);
      byModel.set(r.model, arr);
    }

    const series: EChartsSeriesItem[] = [];
    const colors = ['#4ec9b0', '#569cd6', '#ce9178', '#dcdcaa', '#c586c0', '#9cdcfe'];
    let colorIdx = 0;

    for (const [model, recs] of byModel) {
      const color = colors[colorIdx % colors.length];
      colorIdx++;

      if (mode === 'line') {
        const data = recs.map(r => [r.timestamp, r.latency_ms] as [string, number]);
        series.push({
          name: model,
          type: 'line',
          data,
          smooth: true,
          symbol: 'circle',
          symbolSize: 3,
          lineStyle: { color, width: 1.5 },
          itemStyle: { color },
        });
      } else {
        // Candlestick: group by minute, get OHLC
        // open  = first value in chronological order during this minute
        // close = last value in chronological order
        // high  = maximum of the minute's values
        // low   = minimum of the minute's values
        const ohlc: OhlcEntry[] = [];
        const minuteMap = new Map<string, number[]>();
        for (const r of recs) {
          const minute = r.timestamp.slice(0, 16);
          const arr = minuteMap.get(minute) || [];
          arr.push(r.latency_ms);
          minuteMap.set(minute, arr);
        }
        for (const [minute, vals] of minuteMap) {
          const openVal = vals[0];
          const closeVal = vals[vals.length - 1];
          const highVal = Math.max(...vals);
          const lowVal = Math.min(...vals);
          ohlc.push([minute, openVal, closeVal, lowVal, highVal]);
        }
        series.push({
          name: model,
          type: 'candlestick',
          data: ohlc,
          itemStyle: { color, color0: color + '80', borderColor: color, borderColor0: color + '80' },
        });
      }
    }

    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: {
        data: [...byModel.keys()],
        textStyle: { color: '#858585', fontSize: 11 },
        top: 0,
      },
      grid: { top: 40, right: 16, bottom: 30, left: 50 },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: '#3c3c3c' } },
        axisLabel: { color: '#858585', fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        name: 'ms',
        axisLine: { lineStyle: { color: '#3c3c3c' } },
        axisLabel: { color: '#858585', fontSize: 10 },
        splitLine: { lineStyle: { color: '#3c3c3c' } },
      },
      dataZoom: [{ type: 'inside', start: 0, end: 100 }],
      series,
    }, true);
  }, [records, mode]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontSize: 13, fontWeight: 600 }}>Latency</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <Button
            size="sm"
            variant={mode === 'line' ? 'default' : 'outline'}
            onClick={() => setMode('line')}
            style={{ padding: '2px 8px', fontSize: 11 }}
          >
            <TrendingUp size={12} /> Line
          </Button>
          <Button
            size="sm"
            variant={mode === 'candlestick' ? 'default' : 'outline'}
            onClick={() => setMode('candlestick')}
            style={{ padding: '2px 8px', fontSize: 11 }}
          >
            <BarChart3 size={12} /> K-line
          </Button>
        </div>
      </div>
      <div
        ref={chartRef}
        style={{ height: '60vh', minHeight: 400, width: '100%' }}
      />
    </div>
  );
}
