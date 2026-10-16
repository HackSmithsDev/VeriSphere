import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshDistortMaterial } from '@react-three/drei'
import { Suspense, useMemo, useRef } from 'react'

function getThemeColor(name) {
  const probe = document.createElement('span')
  probe.style.color = `var(${name})`
  document.body.append(probe)
  const color = getComputedStyle(probe).color
  probe.remove()
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 1
  const context = canvas.getContext('2d', { willReadFrequently: true })
  if (!context) throw new Error('A 2D canvas context is required to read theme colors.')
  context.fillStyle = color
  context.fillRect(0, 0, 1, 1)
  const [red, green, blue] = context.getImageData(0, 0, 1, 1).data
  return `#${[red, green, blue]
    .map((channel) => channel.toString(16).padStart(2, '0'))
    .join('')}`
}

function LearningOrbit({ colors, reducedMotion }) {
  const orb = useRef(null)
  const orbit = useRef(null)

  useFrame((_, delta) => {
    if (reducedMotion) return
    if (orb.current) orb.current.rotation.y += delta * 0.12
    if (orbit.current) orbit.current.rotation.z += delta * 0.035
  })

  return (
    <group>
      <Float
        speed={reducedMotion ? 0 : 0.8}
        floatIntensity={reducedMotion ? 0 : 0.18}
        rotationIntensity={reducedMotion ? 0 : 0.04}
      >
        <group ref={orb}>
          <mesh>
            <icosahedronGeometry args={[0.68, 4]} />
            <MeshDistortMaterial
              color={colors.primary}
              roughness={0.42}
              metalness={0}
              distort={0.16}
              speed={reducedMotion ? 0 : 1.2}
            />
          </mesh>
          <mesh scale={0.71}>
            <icosahedronGeometry args={[0.68, 2]} />
            <meshBasicMaterial
              color={colors.highlight}
              wireframe
              transparent
              opacity={0.18}
            />
          </mesh>
        </group>
      </Float>

      <group ref={orbit} rotation={[0.48, 0.16, -0.25]}>
        <mesh>
          <torusGeometry args={[1.08, 0.012, 10, 120]} />
          <meshBasicMaterial
            color={colors.primary}
            transparent
            opacity={0.42}
          />
        </mesh>
        <mesh rotation={[0.4, 0.8, 0.2]}>
          <torusGeometry args={[1.28, 0.006, 8, 120]} />
          <meshBasicMaterial
            color={colors.accent}
            transparent
            opacity={0.32}
          />
        </mesh>
      </group>

      {[
        [-1.02, 0.42, 0.1],
        [0.96, 0.55, 0.16],
        [0.82, -0.67, 0.14],
        [-0.84, -0.58, 0.18],
      ].map((position, index) => (
        <mesh key={position.join('-')} position={position}>
          <sphereGeometry args={[index === 0 ? 0.065 : 0.048, 20, 20]} />
          <meshBasicMaterial
            color={index % 2 ? colors.accent : colors.highlight}
            toneMapped={false}
          />
        </mesh>
      ))}
    </group>
  )
}

export default function HeroScene() {
  const colors = useMemo(
    () => ({
      primary: getThemeColor('--theme-primary'),
      accent: getThemeColor('--theme-success'),
      highlight: getThemeColor('--theme-primary-hover'),
    }),
    [],
  )
  const reducedMotion = useMemo(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    [],
  )

  return (
    <div className="hero-scene" aria-hidden="true">
      <Canvas
        dpr={[1, 1.5]}
        camera={{ position: [0, 0, 4.2], fov: 42 }}
        gl={{ alpha: true, antialias: true, powerPreference: 'low-power' }}
        fallback={<div className="hero-scene-fallback" />}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.65} />
          <directionalLight position={[2, 3, 4]} intensity={1.2} />
          <LearningOrbit colors={colors} reducedMotion={reducedMotion} />
        </Suspense>
      </Canvas>
    </div>
  )
}
