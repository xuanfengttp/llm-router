import { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import type { LatencyRecordOut, LatencyDailyOut } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { BarChart3, TrendingUp, CalendarDays } from 'lucide-react';
import { useT } from '@/locales';

interface LatencyChartProps {
  records: LatencyRecordOut[];
  dailyRecords: LatencyDailyOut[];
}

type ChartMode = 'line' | 'candlestick' | 'daily';

/** ECharts candlestick data point: [timestamp, open, close, low, high] */
type OhlcEntry = [string, number, number, number, number];

export function LatencyChart({ records, dailyRecords }: LatencyChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const echartsRef = useRef<echarts.ECharts | null>(null);
  const [mode, setMode] = useState<ChartMode>('line');
  const t = useT();

  useEffect(() => {
    if (!chartRef.current) return;
    if (!echartsRef.current) {
      echartsRef.current = echarts.init(chartRef.current, 'dark');
    }
    // ResizeObserver：容器尺寸变化时自动缩放 ECharts
    const observer = new ResizeObserver(() => {
      echartsRef.current?.resize();
    });
    observer.observe(chartRef.current);
    return () => {
      observer.disconnect();
      echartsRef.current?.dispose();
      echartsRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = echartsRef.current;
    if (!chart) return;

    const colors = ['#4ec9b0', '#569cd6', '#ce9178', '#dcdcaa', '#c586c0', '#9cdcfe'];

    // ── Daily mode ──
    if (mode === 'daily' && dailyRecords.length > 0) {
      const byModel = new Map<string, LatencyDailyOut[]>();
      for (const r of dailyRecords) {
        const arr = byModel.get(r.model) || [];
        arr.push(r);
        byModel.set(r.model, arr);
      }

      const series = [];
      const legendData: string[] = [];
      let ci = 0;
      for (const [model, rows] of byModel) {
        const color = colors[ci % colors.length];
        ci++;
        legendData.push(model);

        // Sort by date
        rows.sort((a, b) => a.date.localeCompare(b.date));

        // ECharts time axis needs a date string; "YYYY-MM-DD" works with type:'time'
        const avgData = rows.map(r => [r.date, r.avg_ms] as [string, number]);
        const bandData = rows.map(r => [r.date, r.min_ms, r.max_ms] as [string, number, number]);

        // Avg line
        series.push({
          name: model,
          type: 'line',
          data: avgData,
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: { color, width: 2 },
          itemStyle: { color },
          z: 2,
        });

        // Min–max band (area between min and max)
        series.push({
          name: `${model} (min–max)`,
          type: 'line',
          data: bandData,
          smooth: true,
          symbol: 'none',
          lineStyle: { color: 'transparent', width: 0 },
          areaStyle: { color: color + '30' },
          z: 1,
        });
      }

      chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        legend: {
          data: legendData,
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
      return;
    }

    // ── Line / Candlestick mode ──
    const byModel = new Map<string, LatencyRecordOut[]>();
    for (const r of records) {
      const arr = byModel.get(r.model) || [];
      arr.push(r);
      byModel.set(r.model, arr);
    }

    const series: Array<Record<string, unknown>> = [];
    let colorIdx = 0;

    for (const [model, recs] of byModel) {
      const color = colors[colorIdx % colors.length];
      colorIdx++;

      if (mode === 'line') {
        const data = recs.map(r => [r.timestamp, r.latency_ms]);
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
        const ohlc: OhlcEntry[] = [];
        const minuteMap = new Map<string, number[]>();
        for (const r of recs) {
          const minute = r.timestamp.slice(0, 16);
          const arr = minuteMap.get(minute) || [];
          arr.push(r.latency_ms);
          minuteMap.set(minute, arr);
        }
        for (const [minute, vals] of minuteMap) {
          ohlc.push([minute, vals[0], vals[vals.length - 1], Math.min(...vals), Math.max(...vals)]);
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
  }, [records, dailyRecords, mode]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontSize: 13, fontWeight: 600 }}>{t('延迟')}</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <Button
            size="sm"
            variant={mode === 'line' ? 'default' : 'outline'}
            onClick={() => setMode('line')}
            style={{ padding: '2px 8px', fontSize: 11 }}
          >
            <TrendingUp size={12} /> {t('折线')}
          </Button>
          <Button
            size="sm"
            variant={mode === 'candlestick' ? 'default' : 'outline'}
            onClick={() => setMode('candlestick')}
            style={{ padding: '2px 8px', fontSize: 11 }}
          >
            <BarChart3 size={12} /> {t('K线')}
          </Button>
          <Button
            size="sm"
            variant={mode === 'daily' ? 'default' : 'outline'}
            onClick={() => setMode('daily')}
            style={{ padding: '2px 8px', fontSize: 11 }}
          >
            <CalendarDays size={12} /> {t('日线')}
          </Button>
        </div>
      </div>
      {mode === 'daily' && dailyRecords.length === 0 ? (
        <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: 12 }}>
          {t('暂无日线数据')}
        </div>
      ) : (
        <div
          ref={chartRef}
          style={{ height: 260, width: '100%' }}
        />
      )}
    </div>
  );
}
