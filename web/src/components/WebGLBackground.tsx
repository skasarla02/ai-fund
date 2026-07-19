import { useEffect, useRef } from "react";

const VERTEX_SRC = `attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}`;

const FRAGMENT_SRC = `precision highp float;uniform vec2 r;uniform float t;
float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float n(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<6;i++){v+=a*n(p);p*=2.03;a*=.5;}return v;}
void main(){
  vec2 uv=(gl_FragCoord.xy-.5*r)/r.y; vec2 q=uv*1.5; float tt=t*.035;
  vec2 w=vec2(fbm(q+vec2(tt,0.)),fbm(q+vec2(0.,tt)+3.1));
  float f=fbm(q*1.3+w*1.7+tt);
  vec3 dark=vec3(.082,.078,.114),mint=vec3(.50,.91,.76),iris=vec3(.66,.61,1.0),pink=vec3(1.0,.62,.81);
  vec3 col=dark; float m=smoothstep(.30,.85,f);
  col=mix(col, mix(iris,mint,m), pow(m,1.5)*.16);
  float g1=smoothstep(.70,.90,f); col+=mint*g1*.10;
  float g2=smoothstep(.55,.74,fbm(q*1.1-tt+7.0)); col+=iris*g2*.09;
  float g3=smoothstep(.82,.97,f); col+=pink*g3*.11;
  float vig=smoothstep(1.32,.22,length(uv)); col*=vig; col+=(h(gl_FragCoord.xy)-.5)*.015;
  gl_FragColor=vec4(col,1.);
}`;

/** Ambient pastel-iridescent shader backdrop, fixed behind all page content. */
export function WebGLBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl");
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!gl) return;

    function resize() {
      if (!canvas || !gl) return;
      const scale = Math.min(devicePixelRatio, 1.6);
      canvas.width = innerWidth * scale;
      canvas.height = innerHeight * scale;
      gl.viewport(0, 0, canvas.width, canvas.height);
    }
    resize();
    addEventListener("resize", resize);

    function compile(type: number, src: string) {
      const shader = gl!.createShader(type)!;
      gl!.shaderSource(shader, src);
      gl!.compileShader(shader);
      return shader;
    }
    const program = gl.createProgram()!;
    gl.attachShader(program, compile(gl.VERTEX_SHADER, VERTEX_SRC));
    gl.attachShader(program, compile(gl.FRAGMENT_SHADER, FRAGMENT_SRC));
    gl.linkProgram(program);
    gl.useProgram(program);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const posLoc = gl.getAttribLocation(program, "p");
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

    const rLoc = gl.getUniformLocation(program, "r");
    const tLoc = gl.getUniformLocation(program, "t");
    const t0 = performance.now();
    let raf = 0;

    function frame(now: number) {
      if (!gl || !canvas) return;
      gl.uniform2f(rLoc, canvas.width, canvas.height);
      gl.uniform1f(tLoc, reduce ? 6.0 : (now - t0) / 1000);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      if (!reduce) raf = requestAnimationFrame(frame);
    }
    if (reduce) {
      frame(0);
    } else {
      raf = requestAnimationFrame(frame);
    }

    return () => {
      removeEventListener("resize", resize);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 -z-20 block h-screen w-screen"
      aria-hidden="true"
    />
  );
}
