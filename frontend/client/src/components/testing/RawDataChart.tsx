import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Label
} from 'recharts';

interface DataPoint {
  time: number;
  value: number;
}

interface RawDataChartProps {
  data: DataPoint[];
  xAxisLabel?: string;
  yAxisLabel?: string;
}

export default function RawDataChart({ data = [], xAxisLabel = "Time (s)", yAxisLabel = "Value" }: RawDataChartProps) {
  const chartData = useMemo(() => {
    return data.map((point, idx) => ({
      time: point.time ?? idx,
      value: point.value ?? 0
    }));
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-muted-foreground bg-muted/50 rounded-lg">
        No data available for visualization
      </div>
    );
  }

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 11 }}
            className="text-muted-foreground"
            tickFormatter={(value) => value.toFixed(1)}
          >
            <Label
              value={xAxisLabel}
              position="bottom"
              offset={10}
              style={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
            />
          </XAxis>
          <YAxis
            tick={{ fontSize: 11 }}
            className="text-muted-foreground"
            width={60}
            tickFormatter={(value) => value.toExponential(1)}
          >
            <Label
              value={yAxisLabel}
              angle={-90}
              position="insideLeft"
              offset={5}
              style={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))', textAnchor: 'middle' }}
            />
          </YAxis>
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--popover))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              padding: '8px 12px'
            }}
            labelStyle={{ color: 'hsl(var(--muted-foreground))', fontSize: 11 }}
            itemStyle={{ color: 'hsl(var(--foreground))', fontSize: 12, fontWeight: 500 }}
            formatter={(value: number) => [value.toExponential(3), yAxisLabel]}
            labelFormatter={(label: number) => `Time: ${label.toFixed(3)}s`}
          />
          <Line
            type="monotone"
            dataKey="value"
            className="stroke-primary"
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
