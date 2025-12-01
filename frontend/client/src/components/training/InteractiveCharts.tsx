import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Activity, TrendingDown } from "lucide-react";

interface TrainingHistory {
  accuracy?: number[];
  val_accuracy?: number[];
  loss?: number[];
  val_loss?: number[];
}

interface InteractiveChartsProps {
  history: TrainingHistory | null;
}

function prepareChartData(history: TrainingHistory | null) {
  if (!history) return [];

  const epochs = history.accuracy?.length || history.loss?.length || 0;
  const data = [];

  for (let i = 0; i < epochs; i++) {
    data.push({
      epoch: i + 1,
      "Train Accuracy": history.accuracy?.[i] ? history.accuracy[i] * 100 : undefined,
      "Val Accuracy": history.val_accuracy?.[i] ? history.val_accuracy[i] * 100 : undefined,
      "Train Loss": history.loss?.[i],
      "Val Loss": history.val_loss?.[i],
    });
  }

  return data;
}

export function InteractiveCharts({ history }: InteractiveChartsProps) {
  const [activeTab, setActiveTab] = useState("accuracy");
  const chartData = prepareChartData(history);

  if (!history || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <p>No training history available</p>
      </div>
    );
  }

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="accuracy" className="gap-2">
          <Activity size={16} />
          Accuracy
        </TabsTrigger>
        <TabsTrigger value="loss" className="gap-2">
          <TrendingDown size={16} />
          Loss
        </TabsTrigger>
      </TabsList>

      <TabsContent value="accuracy" className="mt-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Training & Validation Accuracy</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="epoch"
                  label={{ value: "Epoch", position: "insideBottom", offset: -5 }}
                  className="text-xs"
                />
                <YAxis
                  label={{ value: "Accuracy (%)", angle: -90, position: "insideLeft" }}
                  className="text-xs"
                  domain={[0, 100]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--background))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                  formatter={(value: number) => [`${value.toFixed(2)}%`, ""]}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="Train Accuracy"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  type="monotone"
                  dataKey="Val Accuracy"
                  stroke="hsl(var(--chart-2))"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  strokeDasharray="5 5"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="loss" className="mt-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Training & Validation Loss</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="epoch"
                  label={{ value: "Epoch", position: "insideBottom", offset: -5 }}
                  className="text-xs"
                />
                <YAxis
                  label={{ value: "Loss", angle: -90, position: "insideLeft" }}
                  className="text-xs"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--background))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                  formatter={(value: number) => [`${value.toFixed(4)}`, ""]}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="Train Loss"
                  stroke="hsl(var(--destructive))"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  type="monotone"
                  dataKey="Val Loss"
                  stroke="hsl(var(--chart-3))"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  strokeDasharray="5 5"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}
