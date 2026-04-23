
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Float, Stars } from '@react-three/drei';
import { Suspense } from 'react';

function FloatingDoc({ position, color }: { position: [number, number, number], color: string }) {
  return (
    <Float speed={1.2} rotationIntensity={0.4} floatIntensity={1.2}>
      <mesh position={position} castShadow receiveShadow>
        <planeGeometry args={[2, 2.8]} />
        <meshStandardMaterial color={color} transparent opacity={0.7} />
      </mesh>
    </Float>
  );
}

export function Hero3D() {
  return (
    <div className="absolute inset-0 w-full h-full pointer-events-none z-0">
      <Canvas camera={{ position: [0, 0, 10], fov: 50 }} shadows>
        <ambientLight intensity={0.7} />
        <pointLight position={[10, 10, 10]} intensity={1.2} color="#6c63ff" />
        <pointLight position={[-10, -10, 10]} intensity={0.8} color="#38bdf8" />
        <Suspense fallback={null}>
          <FloatingDoc position={[-3, 1, 0]} color="#6c63ff" />
          <FloatingDoc position={[2, -1.5, 0]} color="#38bdf8" />
          <FloatingDoc position={[0, 2.5, 0]} color="#a78bfa" />
          <FloatingDoc position={[-1.5, -2, 0]} color="#34d399" />
          <FloatingDoc position={[3, 2, 0]} color="#fbbf24" />
          <Stars radius={12} depth={40} count={200} factor={0.5} fade speed={1} />
        </Suspense>
        <OrbitControls enableZoom={false} enablePan={false} enableRotate={false} />
      </Canvas>
    </div>
  );
}
