import { PrismaClient, User } from '@school-erp/database';
import * as argon2 from 'argon2';
import * as jwt from 'jsonwebtoken';

export interface LoginInput {
  tenantId: string;
  email: string;
  password: string;
}

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
}

export interface TokenPayload {
  userId: string;
  tenantId: string;
  email: string;
}

export interface AuthServiceConfig {
  jwtSecret: string;
  jwtExpiresIn?: string;      // e.g., '15m'
  refreshExpiresIn?: string;  // e.g., '7d'
}

export class AuthService {
  private jwtSecret: string;
  private jwtExpiresIn: string;
  private refreshExpiresIn: string;

  constructor(
    private prisma: PrismaClient,
    config: AuthServiceConfig
  ) {
    this.jwtSecret = config.jwtSecret;
    this.jwtExpiresIn = config.jwtExpiresIn || '15m';
    this.refreshExpiresIn = config.refreshExpiresIn || '7d';
  }

  async hashPassword(password: string): Promise<string> {
    return argon2.hash(password, {
      type: argon2.argon2id,
      memoryCost: 65536,
      timeCost: 3,
      parallelism: 4,
    });
  }

  async verifyPassword(hash: string, password: string): Promise<boolean> {
    return argon2.verify(hash, password);
  }

  async login(input: LoginInput): Promise<{ user: User; tokens: TokenPair }> {
    const user = await this.prisma.user.findFirst({
      where: {
        tenantId: input.tenantId,
        email: input.email,
        deletedAt: null,
      },
    });

    if (!user) {
      throw new Error('Invalid email or password');
    }

    if (user.status === 'SUSPENDED') {
      throw new Error('Account is suspended');
    }

    if (user.status === 'ARCHIVED') {
      throw new Error('Account is archived');
    }

    if (!user.passwordHash) {
      throw new Error('Password not set. Please use invite link to set password.');
    }

    const isValid = await this.verifyPassword(user.passwordHash, input.password);
    if (!isValid) {
      throw new Error('Invalid email or password');
    }

    // Activate user if they were invited
    if (user.status === 'INVITED') {
      await this.prisma.user.update({
        where: { id: user.id },
        data: { status: 'ACTIVE' },
      });
    }

    const tokens = this.generateTokens({
      userId: user.id,
      tenantId: user.tenantId,
      email: user.email,
    });

    return { user, tokens };
  }

  generateTokens(payload: TokenPayload): TokenPair {
    const accessToken = jwt.sign(payload, this.jwtSecret, {
      expiresIn: this.jwtExpiresIn,
    });

    const refreshToken = jwt.sign(
      { userId: payload.userId, type: 'refresh' },
      this.jwtSecret,
      { expiresIn: this.refreshExpiresIn }
    );

    return { accessToken, refreshToken };
  }

  async refreshTokens(refreshToken: string): Promise<TokenPair> {
    try {
      const decoded = jwt.verify(refreshToken, this.jwtSecret) as {
        userId: string;
        type: string;
      };

      if (decoded.type !== 'refresh') {
        throw new Error('Invalid token type');
      }

      const user = await this.prisma.user.findFirst({
        where: { id: decoded.userId, deletedAt: null },
      });

      if (!user) {
        throw new Error('User not found');
      }

      if (user.status !== 'ACTIVE') {
        throw new Error('User account is not active');
      }

      return this.generateTokens({
        userId: user.id,
        tenantId: user.tenantId,
        email: user.email,
      });
    } catch (error) {
      throw new Error('Invalid or expired refresh token');
    }
  }

  async verifyAccessToken(token: string): Promise<TokenPayload> {
    try {
      const decoded = jwt.verify(token, this.jwtSecret) as TokenPayload;
      return decoded;
    } catch (error) {
      throw new Error('Invalid or expired access token');
    }
  }

  async setPassword(userId: string, password: string): Promise<void> {
    const user = await this.prisma.user.findFirst({
      where: { id: userId, deletedAt: null },
    });

    if (!user) {
      throw new Error('User not found');
    }

    if (user.passwordHash) {
      throw new Error('Password already set. Use change password instead.');
    }

    const passwordHash = await this.hashPassword(password);

    await this.prisma.user.update({
      where: { id: userId },
      data: {
        passwordHash,
        status: 'ACTIVE',
      },
    });
  }

  async changePassword(
    userId: string,
    currentPassword: string,
    newPassword: string
  ): Promise<void> {
    const user = await this.prisma.user.findFirst({
      where: { id: userId, deletedAt: null },
    });

    if (!user || !user.passwordHash) {
      throw new Error('User not found or password not set');
    }

    const isValid = await this.verifyPassword(user.passwordHash, currentPassword);
    if (!isValid) {
      throw new Error('Current password is incorrect');
    }

    const passwordHash = await this.hashPassword(newPassword);

    await this.prisma.user.update({
      where: { id: userId },
      data: { passwordHash },
    });
  }
}
