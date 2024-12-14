declare module 'd3' {
  export * from 'd3-selection';
  export * from 'd3-scale';
  export * from 'd3-zoom';
  export * from 'd3-force';
  export * from 'd3-drag';
  export * from 'd3-interpolate';
  export * from 'd3-array';
  
  // 补充必要的类型定义
  export interface D3ZoomEvent {
    transform: {
      x: number;
      y: number;
      k: number;
      toString(): string;
      apply(point: [number, number]): [number, number];
    };
    sourceEvent: any;
    target: any;
  }

  export interface SimulationNode extends d3.SimulationNodeDatum {
    x?: number;
    y?: number;
    fx?: number | null;
    fy?: number | null;
    scale: number;
    similarity: number;
    name: string;
    extra_info?: {
      language?: string;
      stars?: number;
      description?: string;
      [key: string]: any;
    };
  }

  export interface D3DragEvent {
    x: number;
    y: number;
    dx: number;
    dy: number;
    active: boolean;
    sourceEvent: any;
  }
}