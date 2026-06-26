import { PrismaClient } from '@school-erp/database';

export interface GenerateIdentifierInput {
  institutionId: string;
  pattern: string;
  year?: number;
}

export class IdentifierService {
  constructor(private prisma: PrismaClient) {}

  async generate(input: GenerateIdentifierInput): Promise<string> {
    const { institutionId, pattern, year = new Date().getFullYear() } = input;

    // Validate pattern
    this.validatePattern(pattern);

    // Get or create sequence
    const sequence = await this.getOrCreateSequence(institutionId, pattern, year);

    // Increment sequence atomically
    const newSequence = await this.incrementSequence(sequence.id);

    // Format identifier
    return this.formatIdentifier(pattern, newSequence, year, institutionId);
  }

  private async getOrCreateSequence(
    institutionId: string,
    pattern: string,
    year: number
  ) {
    const existing = await this.prisma.identifierSequence.findFirst({
      where: {
        institutionId,
        pattern,
        year,
      },
    });

    if (existing) {
      return existing;
    }

    // Get tenantId from institution
    const institution = await this.prisma.institution.findUnique({
      where: { id: institutionId },
    });

    if (!institution) {
      throw new Error('Institution not found');
    }

    return this.prisma.identifierSequence.create({
      data: {
        tenantId: institution.tenantId,
        institutionId,
        pattern,
        year,
        currentSequence: 0,
      },
    });
  }

  private async incrementSequence(sequenceId: string): Promise<number> {
    // Use transaction for atomic increment
    const result = await this.prisma.$transaction(async (tx) => {
      const sequence = await tx.identifierSequence.findUnique({
        where: { id: sequenceId },
      });

      if (!sequence) {
        throw new Error('Sequence not found');
      }

      const newSequence = sequence.currentSequence + 1;

      await tx.identifierSequence.update({
        where: { id: sequenceId },
        data: { currentSequence: newSequence },
      });

      return newSequence;
    });

    return result;
  }

  private formatIdentifier(
    pattern: string,
    sequence: number,
    year: number,
    institutionId: string
  ): string {
    let result = pattern;

    // Replace {YEAR} with current year
    result = result.replace(/\{YEAR\}/g, year.toString());

    // Replace {SEQ:N} with zero-padded sequence
    const seqMatch = result.match(/\{SEQ:(\d+)\}/);
    if (seqMatch) {
      const padding = parseInt(seqMatch[1], 10);
      const paddedSequence = sequence.toString().padStart(padding, '0');
      result = result.replace(/\{SEQ:\d+\}/g, paddedSequence);
    }

    // Replace {INST} with first 3 chars of institution ID
    result = result.replace(/\{INST\}/g, institutionId.substring(0, 3).toUpperCase());

    return result;
  }

  private validatePattern(pattern: string): void {
    const validTokens = ['{YEAR}', '{INST}'];
    const seqPattern = /\{SEQ:\d+\}/;

    // Check for valid tokens
    let tempPattern = pattern;
    for (const token of validTokens) {
      tempPattern = tempPattern.replace(new RegExp(token.replace(/[{}]/g, '\\$&'), 'g'), '');
    }
    tempPattern = tempPattern.replace(seqPattern, '');

    // Check for any remaining curly braces (invalid tokens)
    if (tempPattern.includes('{') || tempPattern.includes('}')) {
      throw new Error(`Invalid pattern: ${pattern}. Contains unrecognized tokens.`);
    }

    // Must contain at least {SEQ:N}
    if (!pattern.includes('{SEQ:')) {
      throw new Error(`Invalid pattern: ${pattern}. Must contain {SEQ:N} token.`);
    }
  }

  async getCurrentSequence(
    institutionId: string,
    pattern: string,
    year?: number
  ): Promise<number> {
    const targetYear = year || new Date().getFullYear();

    const sequence = await this.prisma.identifierSequence.findFirst({
      where: {
        institutionId,
        pattern,
        year: targetYear,
      },
    });

    return sequence?.currentSequence || 0;
  }

  async resetSequence(
    institutionId: string,
    pattern: string,
    year: number
  ): Promise<void> {
    await this.prisma.identifierSequence.updateMany({
      where: {
        institutionId,
        pattern,
        year,
      },
      data: { currentSequence: 0 },
    });
  }
}
