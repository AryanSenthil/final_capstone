import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceArea } from 'recharts';

interface TimeSeriesChartProps {
  data: Array<{ time: number; value: number }>;
  label: string;
  yAxisLabel: string;
  height?: number;
}

export function TimeSeriesChart({ data, label, yAxisLabel, height = 300 }: TimeSeriesChartProps) {
  // Calculate appropriate tick interval based on data range
  const maxTime = data.length > 0 ? Math.max(...data.map(d => d.time)) : 10;
  const tickInterval = maxTime <= 5 ? 0.5 : maxTime <= 10 ? 1 : 2;

  // Generate tick values
  const ticks: number[] = [];
  for (let i = 0; i <= maxTime; i += tickInterval) {
    ticks.push(Number(i.toFixed(1)));
  }

  return (
    <div className="w-full bg-white rounded-lg p-4 border border-gray-200" style={{ height }}>
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
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="time"
            label={{ value: 'Time (s)', position: 'insideBottomRight', offset: -10, fill: '#374151' }}
            stroke="#6b7280"
            fontSize={11}
            ticks={ticks}
            tickFormatter={(val) => val.toFixed(1)}
            domain={[0, maxTime]}
          />
          <YAxis
            label={{ value: yAxisLabel, angle: -90, position: 'insideLeft', offset: 10, fill: '#374151', style: { textAnchor: 'middle' } }}
            stroke="#6b7280"
            fontSize={11}
            tickFormatter={(val) => val.toFixed(1)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#ffffff',
              borderColor: '#e5e7eb',
              borderRadius: '6px',
              fontSize: '12px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
            itemStyle={{ color: '#374151' }}
            labelStyle={{ color: '#6b7280', marginBottom: '4px' }}
            formatter={(value: number) => [value.toFixed(3), yAxisLabel]}
            labelFormatter={(label) => `Time: ${Number(label).toFixed(2)}s`}
          />

          {/* Padding Regions Visualization - Gray Areas */}
          <ReferenceArea x1={0} x2={1} fill="#f3f4f6" fillOpacity={0.8} />
          <ReferenceArea x1={9} x2={10} fill="#f3f4f6" fillOpacity={0.8} />

          <Line
            type="monotone"
            dataKey="value"
            stroke="#1e40af"
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0, fill: '#1e40af' }}
            animationDuration={500}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
