import { useState } from 'react';
import { Image, StyleSheet, Text, View } from 'react-native';

import { type } from '@/tokens/typography';

interface LogoAvatarProps {
  name: string;
  domain?: string;
  logoUrl?: string;
  brandColor?: string;
  size?: number;
  square?: boolean;
}

const PALETTE = ['#FF8A2E', '#FF6A1A', '#FF3B30', '#F2C94C', '#C9B89A', '#8A2A05'];

function hashIndex(input: string, mod: number) {
  let h = 0;
  for (let i = 0; i < input.length; i += 1) h = (h * 31 + input.charCodeAt(i)) | 0;
  return Math.abs(h) % mod;
}

function initialsOf(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
}

export function LogoAvatar({
  name,
  domain,
  logoUrl,
  brandColor,
  size = 44,
  square = true,
}: LogoAvatarProps) {
  const [failed, setFailed] = useState(false);
  const remoteUrl = logoUrl ?? (domain ? `https://logo.clearbit.com/${domain}` : null);
  const radius = square ? size * 0.27 : size / 2;

  if (remoteUrl && !failed) {
    return (
      <View
        style={[
          styles.frame,
          {
            width: size,
            height: size,
            borderRadius: radius,
            backgroundColor: '#FFFFFF',
          },
        ]}
      >
        <Image
          source={{ uri: remoteUrl }}
          style={{
            width: size,
            height: size,
            borderRadius: radius,
            resizeMode: 'contain',
          }}
          onError={() => setFailed(true)}
        />
      </View>
    );
  }

  const fill = brandColor ?? PALETTE[hashIndex(name, PALETTE.length)];
  const initials = initialsOf(name) || '?';

  return (
    <View
      style={[
        styles.frame,
        {
          width: size,
          height: size,
          borderRadius: radius,
          backgroundColor: fill,
        },
      ]}
    >
      <Text
        style={{
          ...type.caption,
          color: '#FFFFFF',
          fontSize: size * 0.36,
          fontWeight: '700',
          letterSpacing: 0.5,
        }}
      >
        {initials}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
});
