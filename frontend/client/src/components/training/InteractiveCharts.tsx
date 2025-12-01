import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Activity, TrendingDown, Download } from "lucide-react";
import { useRoute } from "wouter";

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
      "Training Accuracy": history.accuracy?.[i] ? history.accuracy[i] * 100 : undefined,
      "Validation Accuracy": history.val_accuracy?.[i] ? history.val_accuracy[i] * 100 : undefined,
      "Training Loss": history.loss?.[i],
      "Validation Loss": history.val_loss?.[i],
    });
  }

  return data;
}

export function InteractiveCharts({ history }: InteractiveChartsProps) {
  const [activeTab, setActiveTab] = useState("accuracy");
  const [, params] = useRoute("/models/:id");
  const modelId = params?.id;
  const chartData = prepareChartData(history);

  const downloadCSV = (type: 'accuracy' | 'loss') => {
    if (!history || !modelId) return;

    let csvContent = "";
    let filename = "";

    if (type === 'accuracy') {
      csvContent = "Epoch,Training Accuracy,Validation Accuracy\n";
      const epochs = history.accuracy?.length || 0;
      for (let i = 0; i < epochs; i++) {
        const trainAcc = history.accuracy?.[i] ? (history.accuracy[i] * 100).toFixed(4) : "";
        const valAcc = history.val_accuracy?.[i] ? (history.val_accuracy[i] * 100).toFixed(4) : "";
        csvContent += `${i + 1},${trainAcc},${valAcc}\n`;
      }
      filename = `${modelId}_training_accuracy.csv`;
    } else {
      csvContent = "Epoch,Training Loss,Validation Loss\n";
      const epochs = history.loss?.length || 0;
      for (let i = 0; i < epochs; i++) {
        const trainLoss = history.loss?.[i]?.toFixed(6) || "";
        const valLoss = history.val_loss?.[i]?.toFixed(6) || "";
        csvContent += `${i + 1},${trainLoss},${valLoss}\n`;
      }
      filename = `${modelId}_training_loss.csv`;
    }

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

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
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-lg">Training & Validation Accuracy</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadCSV('accuracy')}
              className="h-8 hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
            >
              <Download className="h-3.5 w-3.5 mr-1.5" />
              Export CSV
            </Button>
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
                <Legend iconSize={14} wrapperStyle={{ paddingTop: "20px" }} />
                <Line
                  type="monotone"
                  dataKey="Training Accuracy"
                  name="Training Accuracy"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  type="monotone"
                  dataKey="Validation Accuracy"
                  name="Validation Accuracy"
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
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-lg">Training & Validation Loss</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadCSV('loss')}
              className="h-8 hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
            >
              <Download className="h-3.5 w-3.5 mr-1.5" />
              Export CSV
            </Button>
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
                <Legend iconSize={14} wrapperStyle={{ paddingTop: "20px" }} />
                <Line
                  type="monotone"
                  dataKey="Training Loss"
                  name="Training Loss"
                  stroke="hsl(var(--destructive))"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  type="monotone"
                  dataKey="Validation Loss"
                  name="Validation Loss"
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
