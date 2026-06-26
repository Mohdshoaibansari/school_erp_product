import { PrismaClient, OtpRecord, OtpPurpose } from '@school-erp/database';
import * as argon2 from 'argon2';
import * as crypto from 'crypto';

export interface RequestOtpInput {
  tenantId: string;
  email: string;
  purpose: OtpPurpose;
}

export interface VerifyOtpInput {
  tenantId: string;
  email: string;
  code: string;
  purpose: OtpPurpose;
}

export class OtpService {
  private readonly defaultExpiryMinutes = 10;
  private readonly defaultMaxAttempts = 3;

  constructor(private prisma: PrismaClient) {}

  async requestOtp(input: RequestOtpInput): Promise<{ expiresAt: Date }> {
    const { tenantId, email, purpose } = input;

    // Invalidate any existing OTPs for this email and purpose
    await this.prisma.otpRecord.updateMany({
      where: {
        tenantId,
        email,
        purpose,
        usedAt: null,
        expiresAt: { gt: new Date() },
      },
      data: {
        expiresAt: new Date(), // Expire immediately
      },
    });

    // Generate 6-digit code
    const code = this.generateCode();
    const codeHash = await argon2.hash(code);

    // Calculate expiry
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + this.defaultExpiryMinutes);

    // Store OTP
    await this.prisma.otpRecord.create({
      data: {
        tenantId,
        email,
        codeHash,
        purpose,
        expiresAt,
        maxAttempts: this.defaultMaxAttempts,
      },
    });

    return { expiresAt };
  }

  async verifyOtp(input: VerifyOtpInput): Promise<boolean> {
    const { tenantId, email, code, purpose } = input;

    // Find valid OTP
    const otpRecord = await this.prisma.otpRecord.findFirst({
      where: {
        tenantId,
        email,
        purpose,
        usedAt: null,
        expiresAt: { gt: new Date() },
      },
      orderBy: { createdAt: 'desc' },
    });

    if (!otpRecord) {
      throw new Error('Invalid or expired OTP');
    }

    // Check attempts
    if (otpRecord.attempts >= otpRecord.maxAttempts) {
      throw new Error('Maximum OTP attempts exceeded');
    }

    // Verify code
    const isValid = await argon2.verify(otpRecord.codeHash, code);

    if (!isValid) {
      // Increment attempts
      await this.prisma.otpRecord.update({
        where: { id: otpRecord.id },
        data: { attempts: otpRecord.attempts + 1 },
      });

      throw new Error('Invalid OTP code');
    }

    // Mark as used
    await this.prisma.otpRecord.update({
      where: { id: otpRecord.id },
      data: { usedAt: new Date() },
    });

    return true;
  }

  private generateCode(): string {
    // Generate 6-digit code
    return crypto.randomInt(100000, 999999).toString();
  }

  async getOtpStatus(
    tenantId: string,
    email: string,
    purpose: OtpPurpose
  ): Promise<{ hasActiveOtp: boolean; expiresAt?: Date; attemptsRemaining?: number }> {
    const otpRecord = await this.prisma.otpRecord.findFirst({
      where: {
        tenantId,
        email,
        purpose,
        usedAt: null,
        expiresAt: { gt: new Date() },
      },
      orderBy: { createdAt: 'desc' },
    });

    if (!otpRecord) {
      return { hasActiveOtp: false };
    }

    return {
      hasActiveOtp: true,
      expiresAt: otpRecord.expiresAt,
      attemptsRemaining: otpRecord.maxAttempts - otpRecord.attempts,
    };
  }
}
