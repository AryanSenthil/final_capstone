import { useState, useEffect } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceArea } from 'recharts';

interface TimeSeriesChartProps {
  data: Array<{ time: number; value: number }>;
  label: string;
  yAxisLabel: string;
  height?: number;
}

export function TimeSeriesChart({ data, label, yAxisLabel, height = 300 }: TimeSeriesChartProps) {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // Check initial theme
    const checkTheme = () => {
      setIsDark(document.documentElement.classList.contains('dark'));
    };

    checkTheme();

    // Watch for theme changes
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => observer.disconnect();
  }, []);

  // Calculate appropriate tick interval based on data range
  const maxTime = data.length > 0 ? Math.max(...data.map(d => d.time)) : 10;
  const tickInterval = maxTime <= 5 ? 0.5 : maxTime <= 10 ? 1 : 2;

  // Generate tick values
  const ticks: number[] = [];
  for (let i = 0; i <= maxTime; i += tickInterval) {
    ticks.push(Number(i.toFixed(1)));
  }

  // Theme colors
  const colors = isDark ? {
    // Dark mode colors
    grid: '#374151',
    axis: '#9ca3af',
    label: '#e5e7eb',
    tick: '#d1d5db',
    line: '#60a5fa',
    tooltipBg: '#1f2937',
    tooltipBorder: '#374151',
    tooltipText: '#f3f4f6',
    tooltipLabel: '#9ca3af',
    refArea: '#4b5563',  // gray-600 - visible grey on black
    refAreaOpacity: 0.7,
  } : {
    // Light mode colors
    grid: '#e5e7eb',
    axis: '#6b7280',
    label: '#374151',
    tick: '#374151',
    line: '#1e40af',
    tooltipBg: '#ffffff',
    tooltipBorder: '#e5e7eb',
    tooltipText: '#374151',
    tooltipLabel: '#6b7280',
    refArea: '#f3f4f6',  // gray-100 - light grey on white
    refAreaOpacity: 0.8,
  };

  return (
    <div
      className="w-full rounded-lg p-4 border border-border bg-white dark:bg-black"
      style={{ height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{
            top: 20,
            right: 30,
            left: 20,
            bottom: 20,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} strokeWidth={1} />
          <XAxis
            dataKey="time"
            label={{ value: 'Time (s)', position: 'insideBottomRight', offset: -10, fill: colors.label, fontWeight: 'bold' }}
            stroke={colors.axis}
            strokeWidth={1.5}
            fontSize={11}
            fontWeight="bold"
            ticks={ticks}
            tickFormatter={(val) => val.toFixed(1)}
            domain={[0, maxTime]}
            tick={{ fill: colors.tick, fontWeight: 'bold' }}
          />
          <YAxis
            label={{ value: yAxisLabel, angle: -90, position: 'insideLeft', offset: 10, fill: colors.label, style: { textAnchor: 'middle', fontWeight: 'bold' } }}
            stroke={colors.axis}
            strokeWidth={1.5}
            fontSize={11}
            fontWeight="bold"
            tickFormatter={(val) => val.toFixed(1)}
            tick={{ fill: colors.tick, fontWeight: 'bold' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: colors.tooltipBg,
              borderColor: colors.tooltipBorder,
              borderRadius: '6px',
              fontSize: '12px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              color: colors.tooltipText
            }}
            itemStyle={{ color: colors.tooltipText }}
            labelStyle={{ color: colors.tooltipLabel, marginBottom: '4px' }}
            formatter={(value: number) => [value.toFixed(3), yAxisLabel]}
            labelFormatter={(label) => `Time: ${Number(label).toFixed(2)}s`}
          />

          {/* Padding Regions Visualization */}
          <ReferenceArea x1={0} x2={1} fill={colors.refArea} fillOpacity={colors.refAreaOpacity} />
          <ReferenceArea x1={9} x2={10} fill={colors.refArea} fillOpacity={colors.refAreaOpacity} />

          <Line
            type="monotone"
            dataKey="value"
            stroke={colors.line}
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 5, strokeWidth: 0, fill: colors.line }}
            animationDuration={500}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
